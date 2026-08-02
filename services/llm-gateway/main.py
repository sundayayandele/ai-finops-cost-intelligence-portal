"""
Unified LLM Gateway — FastAPI + LiteLLM
Provides a single OpenAI-compatible API that transparently routes to:
  - Azure OpenAI (GPT-4o, GPT-4o-mini, o3-mini)
  - OpenStack vLLM/Ollama (Llama-3, Mistral, Mixtral, DeepSeek)
Includes: semantic caching, cost injection, Kafka event emission
"""
import os, hashlib, orjson, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import litellm
from litellm import acompletion
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer
import numpy as np

app   = FastAPI(title="Unified LLM Gateway", version="2.0")
redis: aioredis.Redis = None
kafka: AIOKafkaProducer = None

# ── Provider routing map ────────────────────────────────────────────────
PROVIDER_MAP = {
    "azure": {
        "gpt-4o":      "azure/gpt-4o",
        "gpt-4o-mini": "azure/gpt-4o-mini",
        "gpt-4":       "azure/gpt-4",
        "o3-mini":     "azure/o3-mini",
        "text-embedding-3-small": "azure/text-embedding-3-small",
        "text-embedding-3-large": "azure/text-embedding-3-large",
    },
    "openstack": {
        "llama-3-70b":  "openai/meta-llama/Llama-3-70B-Instruct",
        "llama-3-8b":   "openai/meta-llama/Llama-3-8B-Instruct",
        "mistral-7b":   "openai/mistralai/Mistral-7B-Instruct-v0.3",
        "mixtral-8x7b": "openai/mistralai/Mixtral-8x7B-Instruct-v0.1",
        "deepseek-r1":  "openai/deepseek-ai/DeepSeek-R1",
    },
}

# ── Cost rates per 1K tokens ($/1K) ────────────────────────────────────
COST_PER_1K = {
    "gpt-4o":      {"in": 0.0025,  "out": 0.0100},
    "gpt-4o-mini": {"in": 0.000150,"out": 0.000600},
    "gpt-4":       {"in": 0.030,   "out": 0.060},
    "o3-mini":     {"in": 0.0011,  "out": 0.0044},
    "llama-3-70b": {"in": 0.0003,  "out": 0.0006},
    "llama-3-8b":  {"in": 0.0001,  "out": 0.0002},
    "mistral-7b":  {"in": 0.00005, "out": 0.0001},
    "mixtral-8x7b":{"in": 0.00015, "out": 0.0003},
    "deepseek-r1": {"in": 0.0002,  "out": 0.0004},
}

# ── Simple routing policy ────────────────────────────────────────────────
DATA_RESIDENCY_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4", "o3-mini"}

def choose_cloud(model: str, requested_cloud: str, data_residency: bool = False) -> str:
    """Select cloud based on policy: data residency, cost, availability."""
    if data_residency:
        return "azure"  # regulated data must stay in Azure (or reverse if on-prem required)
    if requested_cloud in ("azure", "openstack"):
        return requested_cloud
    # Auto: prefer OpenStack for cost if model available
    if model in PROVIDER_MAP["openstack"]:
        return "openstack"
    return "azure"


def calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = COST_PER_1K.get(model, {"in": 0.002, "out": 0.002})
    return round(prompt_tokens / 1000 * rates["in"] + completion_tokens / 1000 * rates["out"], 8)


async def semantic_hash(messages: list) -> str:
    """Fast hash of messages list for cache key."""
    content = "||".join(m.get("content", "") for m in messages)
    return "llm:" + hashlib.sha256(content.encode()).hexdigest()


@app.on_event("startup")
async def startup():
    global redis, kafka
    redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"), decode_responses=False)
    kafka = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        value_serializer=lambda v: orjson.dumps(v))
    await kafka.start()


@app.on_event("shutdown")
async def shutdown():
    if kafka: await kafka.stop()
    if redis: await redis.close()


@app.post("/v1/chat/completions")
async def chat_completions(req: Request):
    body   = await req.json()
    model  = body.get("model", "gpt-4o-mini")
    msgs   = body.get("messages", [])
    stream = body.get("stream", False)
    team   = req.headers.get("X-Team", "unknown")
    cloud  = req.headers.get("X-Cloud", "auto")
    data_r = req.headers.get("X-Data-Residency", "false").lower() == "true"
    session= req.headers.get("X-Agent-Session-Id")

    # 1. Check semantic cache
    cache_key = await semantic_hash(msgs)
    cached    = await redis.get(cache_key)
    if cached:
        resp = orjson.loads(cached)
        await kafka.send("azure.openai.usage" if cloud == "azure" else "openstack.vllm.usage", {
            "cloud": cloud, "model": model, "team": team,
            "cached_tokens": resp.get("usage", {}).get("total_tokens", 0),
            "cost_usd": 0.0, "agent_session_id": session, "cache_hit": True,
        })
        resp["_finops"] = {"cost_usd": 0.0, "cloud": cloud, "cache_hit": True}
        return JSONResponse(resp)

    # 2. Choose cloud and route
    selected_cloud = choose_cloud(model, cloud, data_r)
    routed_model   = PROVIDER_MAP.get(selected_cloud, {}).get(model)
    if not routed_model:
        raise HTTPException(400, f"Model '{model}' not available on cloud '{selected_cloud}'")

    api_key  = "none" if selected_cloud == "openstack" else None
    base_url = os.getenv("VLLM_BASE_URL") if selected_cloud == "openstack" else None

    start_ts = time.perf_counter()
    response = await acompletion(
        model=routed_model, messages=msgs, stream=stream,
        api_base=base_url, api_key=api_key,
    )
    latency_ms = round((time.perf_counter() - start_ts) * 1000, 1)

    result = response.model_dump()
    usage  = result.get("usage", {})
    cost   = calc_cost(model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))

    # 3. Emit Kafka event
    topic = "azure.openai.usage" if selected_cloud == "azure" else "openstack.vllm.usage"
    await kafka.send(topic, {
        "cloud": selected_cloud, "model": model, "team": team,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cost_usd": cost, "latency_ms": latency_ms,
        "agent_session_id": session,
    })

    # 4. Cache response (1 hour TTL)
    await redis.setex(cache_key, 3600, orjson.dumps(result))

    result["_finops"] = {
        "cost_usd": cost, "cloud": selected_cloud,
        "model": model, "latency_ms": latency_ms, "cache_hit": False,
    }
    return JSONResponse(result)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "llm-gateway"}


@app.get("/v1/models")
async def list_models():
    models = []
    for cloud, m in PROVIDER_MAP.items():
        for model_name in m:
            models.append({"id": model_name, "cloud": cloud,
                           "rates": COST_PER_1K.get(model_name, {})})
    return {"object": "list", "data": models}
