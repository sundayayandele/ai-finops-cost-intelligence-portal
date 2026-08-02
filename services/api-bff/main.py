"""
FastAPI BFF — Backend for Frontend
Serves the React dashboard via REST endpoints and WebSocket real-time streams.
Dual-cloud: filter by cloud=azure|openstack|all
"""
import os, asyncio, orjson
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Literal, Optional
import asyncpg
import clickhouse_connect
from aiokafka import AIOKafkaConsumer
import httpx


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ts_pool = await asyncpg.create_pool(
        dsn=os.environ["TIMESCALE_DSN"], min_size=2, max_size=20)
    app.state.ch = clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        database="ai_finops",
    )
    yield
    await app.state.ts_pool.close()


app = FastAPI(title="AI FinOps BFF", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


def get_ts(request): return request.app.state.ts_pool
def get_ch(request): return request.app.state.ch


# ── Cost Summary ──────────────────────────────────────────────────────────
@app.get("/api/v1/costs/summary")
async def cost_summary(
    cloud:  Literal["azure", "openstack", "all"] = "all",
    period: str = "MTD",
    team:   Optional[str] = None,
    env:    Optional[str] = None,
    request = None,
):
    pool         = request.app.state.ts_pool
    cloud_filter = "" if cloud == "all" else f"AND cloud = '{cloud}'"
    team_filter  = "" if not team else f"AND team = '{team}'"
    env_filter   = "" if not env  else f"AND env = '{env}'"
    period_sql   = {
        "MTD":  "time >= date_trunc('month', now())",
        "7d":   "time >= now() - INTERVAL '7 days'",
        "30d":  "time >= now() - INTERVAL '30 days'",
        "YTD":  "time >= date_trunc('year', now())",
    }.get(period, "time >= date_trunc('month', now())")

    rows = await pool.fetch(f"""
        SELECT
            cloud, workload_type, model_name, team, env,
            SUM(cost_usd)                    AS total_usd,
            SUM(prompt_tokens)               AS prompt_tokens,
            SUM(completion_tokens)           AS completion_tokens,
            SUM(cached_tokens)               AS cached_tokens,
            SUM(gpu_hours)                   AS gpu_hours,
            COUNT(*)                         AS events,
            SUM(tool_calls)                  AS total_tool_calls
        FROM ai_costs
        WHERE {period_sql} {cloud_filter} {team_filter} {env_filter}
        GROUP BY cloud, workload_type, model_name, team, env
        ORDER BY total_usd DESC
        LIMIT 500
    """)
    return {"period": period, "cloud": cloud, "data": [dict(r) for r in rows]}


# ── Time Series ───────────────────────────────────────────────────────────
@app.get("/api/v1/costs/timeseries")
async def cost_timeseries(
    cloud:     Literal["azure", "openstack", "all"] = "all",
    granularity: Literal["hour", "day", "week"] = "day",
    days:      int = 30,
    request    = None,
):
    pool        = request.app.state.ts_pool
    bucket      = {"hour": "1 hour", "day": "1 day", "week": "1 week"}[granularity]
    view        = "costs_1h" if granularity == "hour" else "costs_1d"
    cloud_filter = "" if cloud == "all" else f"AND cloud = '{cloud}'"
    rows = await pool.fetch(f"""
        SELECT bucket, cloud, SUM(total_cost) AS cost_usd, SUM(total_gpu_hours) AS gpu_hours
        FROM {view}
        WHERE bucket >= NOW() - INTERVAL '{days} days' {cloud_filter}
        GROUP BY bucket, cloud ORDER BY bucket
    """)
    return {"granularity": granularity, "days": days, "data": [dict(r) for r in rows]}


# ── Cross-Cloud Comparison ────────────────────────────────────────────────
@app.get("/api/v1/costs/by-cloud")
async def cost_by_cloud(days: int = 30, request=None):
    pool = request.app.state.ts_pool
    rows = await pool.fetch("""
        SELECT cloud,
               SUM(cost_usd)          AS total_cost,
               SUM(prompt_tokens + completion_tokens) AS total_tokens,
               SUM(gpu_hours)         AS total_gpu_hours,
               COUNT(DISTINCT team)   AS team_count,
               COUNT(DISTINCT model_name) AS model_count,
               AVG(cost_usd)          AS avg_cost_per_event
        FROM ai_costs
        WHERE time >= NOW() - INTERVAL $1
        GROUP BY cloud
    """, f"{days} days")
    return {"days": days, "clouds": [dict(r) for r in rows]}


# ── Forecast ──────────────────────────────────────────────────────────────
@app.get("/api/v1/forecast/{cloud}/{horizon}")
async def get_forecast(
    cloud:   Literal["azure", "openstack", "combined"],
    horizon: int = 30,
    budget:  float = 100_000,
):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"http://forecast-engine:8024/forecast/{cloud}/{horizon}",
            params={"budget": budget})
    return r.json()


# ── Anomalies ─────────────────────────────────────────────────────────────
@app.get("/api/v1/anomalies")
async def get_anomalies(
    cloud:    Literal["azure", "openstack", "all"] = "all",
    severity: Optional[str] = None,
    limit:    int = 100,
    request   = None,
):
    pool = request.app.state.ts_pool
    cloud_filter    = "" if cloud == "all" else f"AND cloud = '{cloud}'"
    severity_filter = "" if not severity else f"AND severity = '{severity}'"
    rows = await pool.fetch(f"""
        SELECT * FROM ai_anomalies
        WHERE detected_at >= NOW() - INTERVAL '24 hours'
              {cloud_filter} {severity_filter}
        ORDER BY detected_at DESC LIMIT $1
    """, limit)
    return {"anomalies": [dict(r) for r in rows]}


# ── Recommendations ────────────────────────────────────────────────────────
@app.get("/api/v1/recommendations")
async def get_recommendations(request=None):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get("http://recommendation-svc:8025/recommendations")
    return r.json()


# ── FinOps AI Assistant ───────────────────────────────────────────────────
@app.post("/api/v1/agent/chat")
async def agent_chat(body: dict, request=None):
    """Route FinOps chat to OpenStack vLLM (cost-effective) or Azure GPT-4o-mini."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("http://llm-gateway:8010/v1/chat/completions", json={
            "model": "mistral-7b",  # Default to cheap OpenStack model
            "messages": body.get("messages", []),
            "stream": False,
        }, headers={"X-Cloud": "openstack", "X-Team": "finops-platform"})
    return r.json()


# ── WebSocket: Live cost stream ────────────────────────────────────────────
@app.websocket("/ws/costs/live")
async def ws_costs_live(ws: WebSocket):
    await ws.accept()
    consumer = AIOKafkaConsumer(
        "ai.costs.unified",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        group_id=f"ws-live-{id(ws)}",
        value_deserializer=lambda b: orjson.loads(b),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            e = msg.value
            await ws.send_json({
                "cloud": e.get("cloud"), "cost_usd": e.get("cost_usd"),
                "team": e.get("team"), "model": e.get("model_name"),
                "workload_type": e.get("workload_type"),
                "timestamp": e.get("timestamp"),
            })
    except WebSocketDisconnect:
        pass
    finally:
        await consumer.stop()


# ── WebSocket: Live anomaly stream ────────────────────────────────────────
@app.websocket("/ws/anomalies")
async def ws_anomalies(ws: WebSocket):
    await ws.accept()
    consumer = AIOKafkaConsumer(
        "ai.anomalies",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        group_id=f"ws-anomaly-{id(ws)}",
        value_deserializer=lambda b: orjson.loads(b),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await ws.send_json(msg.value)
    except WebSocketDisconnect:
        pass
    finally:
        await consumer.stop()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-bff", "version": "2.0"}

@app.get("/api/v1/health/full")
async def health_full(request=None):
    pool = request.app.state.ts_pool
    try:
        await pool.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {"api": "ok", "timescaledb": "ok" if db_ok else "error"}
