"""
Model Router Service — FastAPI :8011
Policy-based routing between Azure OpenAI and OpenStack vLLM.
Evaluates: data residency, cost threshold, latency SLA, capability requirements.
"""
import os, yaml, httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI(title="Model Router", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Load routing rules from config
RULES_PATH = os.getenv("ROUTING_RULES_PATH", "/app/config/routing-rules.yaml")
RULES = []
if Path(RULES_PATH).exists():
    with open(RULES_PATH) as f:
        RULES = yaml.safe_load(f).get("rules", [])

# Capability map: models only available on Azure
AZURE_ONLY_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4", "o3-mini", "o1", "o1-mini",
                     "text-embedding-3-small", "text-embedding-3-large"}

# Cost-equivalent mapping: Azure model → OpenStack alternative
MODEL_ALTERNATIVES = {
    "gpt-4o":      {"openstack": "llama-3-70b",  "capability": "high"},
    "gpt-4o-mini": {"openstack": "mistral-7b",   "capability": "medium"},
    "gpt-4":       {"openstack": "llama-3-70b",  "capability": "high"},
}

AZURE_COST_PER_1K = {
    "gpt-4o": {"in": 0.0025, "out": 0.010},
    "gpt-4o-mini": {"in": 0.000150, "out": 0.000600},
}
OS_COST_PER_1K = {
    "llama-3-70b": {"in": 0.0003, "out": 0.0006},
    "mistral-7b":  {"in": 0.00005, "out": 0.0001},
}


def estimate_cost(model: str, cloud: str, prompt_tokens: int = 1000) -> float:
    rates = (AZURE_COST_PER_1K if cloud == "azure" else OS_COST_PER_1K).get(model, {"in": 0.002, "out": 0.002})
    return prompt_tokens / 1000 * rates["in"]


def route_request(model: str, headers: dict, estimated_tokens: int = 1000) -> dict:
    """Apply routing rules in order; return routing decision."""

    # Rule 1: Data residency override
    if headers.get("x-data-residency") in ("eu-regulated", "on-prem-required"):
        os_model = MODEL_ALTERNATIVES.get(model, {}).get("openstack", "llama-3-70b")
        return {"cloud": "openstack", "model": os_model, "reason": "data-residency-policy",
                "override": True}

    # Rule 2: Frontier models → Azure only
    if model in AZURE_ONLY_MODELS and model not in {"gpt-4o-mini"}:
        if headers.get("x-force-openstack") != "true":
            return {"cloud": "azure", "model": model, "reason": "frontier-model-azure-only"}

    # Rule 3: Latency SLA → Azure
    if headers.get("x-latency-sla") == "200ms":
        return {"cloud": "azure", "model": model, "reason": "latency-sla"}

    # Rule 4: Batch / async → OpenStack
    if headers.get("x-request-type") == "batch":
        os_model = MODEL_ALTERNATIVES.get(model, {}).get("openstack", "llama-3-70b")
        return {"cloud": "openstack", "model": os_model, "reason": "batch-async-policy"}

    # Rule 5: Cost threshold — prefer OpenStack if cheaper and model available
    az_cost = estimate_cost(model, "azure", estimated_tokens)
    os_model = MODEL_ALTERNATIVES.get(model, {}).get("openstack")
    if os_model:
        os_cost = estimate_cost(os_model, "openstack", estimated_tokens)
        if az_cost > os_cost * 1.4:   # Azure is >40% more expensive
            return {"cloud": "openstack", "model": os_model, "reason": "cost-optimisation",
                    "az_cost_estimate": az_cost, "os_cost_estimate": os_cost}

    # Default: Azure
    return {"cloud": "azure", "model": model, "reason": "default"}


@app.post("/route")
async def route(request: Request):
    body  = await request.json()
    model = body.get("model", "gpt-4o-mini")
    tokens = body.get("estimated_tokens", 1000)
    decision = route_request(model, dict(request.headers), tokens)
    return {"request_model": model, "decision": decision}


@app.post("/v1/chat/completions")
async def proxy_chat(request: Request):
    """Route then forward to the selected cloud's LLM gateway."""
    body     = await request.json()
    model    = body.get("model", "gpt-4o-mini")
    decision = route_request(model, dict(request.headers))

    target = os.getenv("LLM_GATEWAY_URL", "http://llm-gateway:8010")
    async with httpx.AsyncClient(timeout=120) as client:
        body["model"] = decision["model"]
        r = await client.post(f"{target}/v1/chat/completions", json=body,
            headers={"X-Cloud": decision["cloud"],
                     "X-Routed-By": "model-router",
                     "X-Route-Reason": decision["reason"]})
    return r.json()


@app.get("/routing-rules")
async def get_rules():
    return {"rules": RULES, "model_alternatives": MODEL_ALTERNATIVES}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "model-router"}
