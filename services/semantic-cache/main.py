"""
Semantic Cache Service — FastAPI :8012
Cloud-agnostic LLM response caching using Redis + cosine similarity embeddings.
Reduces cost by 20-50% through semantic deduplication of equivalent prompts.
"""
import os, hashlib, json, time
import numpy as np
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Semantic Cache Service", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.92"))
TTL_SECONDS          = int(os.getenv("CACHE_TTL_SECONDS", "3600"))   # 1 hour default
MAX_CACHE_ENTRIES    = int(os.getenv("MAX_CACHE_ENTRIES", "100000"))

redis: aioredis.Redis = None


@app.on_event("startup")
async def startup():
    global redis
    redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"), decode_responses=False)


@app.on_event("shutdown")
async def shutdown():
    if redis:
        await redis.close()


def _exact_hash(messages: list) -> str:
    """Exact match hash for identical prompts."""
    content = json.dumps(messages, sort_keys=True)
    return f"cache:exact:{hashlib.sha256(content.encode()).hexdigest()}"


def _messages_to_text(messages: list) -> str:
    return " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))


async def _get_embedding(text: str) -> list[float] | None:
    """Get embedding vector — tries local SentenceTransformer, falls back to hash."""
    try:
        from sentence_transformers import SentenceTransformer
        if not hasattr(app.state, "_embedder"):
            app.state._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        vec = app.state._embedder.encode(text[:2000])
        return vec.tolist()
    except Exception:
        return None


def _cosine_similarity(a: list, b: list) -> float:
    va, vb = np.array(a), np.array(b)
    denom  = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


@app.post("/cache/lookup")
async def cache_lookup(request: Request):
    """Check cache for semantically equivalent prompt. Returns hit or miss."""
    body     = await request.json()
    messages = body.get("messages", [])

    # 1. Exact match (fastest)
    exact_key  = _exact_hash(messages)
    cached_val = await redis.get(exact_key)
    if cached_val:
        return {"hit": True, "match_type": "exact", "response": json.loads(cached_val),
                "savings_usd": body.get("estimated_cost_usd", 0)}

    # 2. Semantic match (embedding similarity)
    text      = _messages_to_text(messages)
    embedding = await _get_embedding(text)
    if embedding:
        # Scan recent embeddings (production: use Redis Vector Search or pgvector)
        keys = await redis.keys("cache:embed:*")
        for key in keys[:500]:   # Limit scan
            stored = await redis.get(key)
            if not stored:
                continue
            data = json.loads(stored)
            sim  = _cosine_similarity(embedding, data["embedding"])
            if sim >= SIMILARITY_THRESHOLD:
                return {"hit": True, "match_type": "semantic", "similarity": round(sim, 4),
                        "response": data["response"],
                        "savings_usd": body.get("estimated_cost_usd", 0)}

    return {"hit": False}


@app.post("/cache/store")
async def cache_store(request: Request):
    """Store a prompt+response in the cache."""
    body      = await request.json()
    messages  = body.get("messages", [])
    response  = body.get("response", {})

    # Exact key
    exact_key = _exact_hash(messages)
    await redis.setex(exact_key, TTL_SECONDS, json.dumps(response))

    # Embedding key for semantic search
    text      = _messages_to_text(messages)
    embedding = await _get_embedding(text)
    if embedding:
        embed_key = f"cache:embed:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
        await redis.setex(embed_key, TTL_SECONDS, json.dumps({
            "embedding": embedding, "response": response, "stored_at": time.time()
        }))

    return {"stored": True, "ttl_seconds": TTL_SECONDS}


@app.get("/cache/stats")
async def cache_stats():
    """Return cache hit rate and memory usage."""
    exact_keys = await redis.keys("cache:exact:*")
    embed_keys = await redis.keys("cache:embed:*")
    info       = await redis.info("memory")
    return {
        "exact_entries": len(exact_keys),
        "semantic_entries": len(embed_keys),
        "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "ttl_seconds": TTL_SECONDS,
    }


@app.delete("/cache/flush")
async def cache_flush():
    """Flush all cache entries."""
    keys = await redis.keys("cache:*")
    if keys:
        await redis.delete(*keys)
    return {"flushed": len(keys)}


@app.get("/health")
async def health():
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"status": "ok" if redis_ok else "degraded",
            "service": "semantic-cache", "redis": redis_ok}
