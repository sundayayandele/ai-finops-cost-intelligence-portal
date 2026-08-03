"""
Recommendation Service — FastAPI :8025
Ranked cost-saving recommendations: model routing, cloud migration,
GPU optimisation, and agent loop guardrails — across both clouds.
"""
import os
import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(
        os.environ["TIMESCALE_DSN"], min_size=1, max_size=5)
    yield
    await app.state.pool.close()


app = FastAPI(title="AI FinOps Recommendation Service", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/recommendations")
async def get_recommendations(request: Request):
    pool = request.app.state.pool
    recs = []

    # ── 1. Model downgrade: gpt-4o → gpt-4o-mini (Azure) ─────────────────
    rows = await pool.fetch("""
        SELECT team, SUM(cost_usd) AS cost
        FROM ai_costs
        WHERE time >= NOW() - INTERVAL '30 days'
          AND cloud = 'azure' AND model_name = 'gpt-4o'
        GROUP BY team
        HAVING SUM(cost_usd) > 50
        ORDER BY cost DESC
    """)
    for r in rows:
        cost    = float(r["cost"])
        savings = round(cost * 0.94, 2)   # gpt-4o-mini is ~94% cheaper input
        recs.append({
            "id": f"downgrade-{r['team']}",
            "type": "MODEL_ROUTING",
            "priority": "high" if savings > 200 else "medium",
            "title": f"Route '{r['team']}' simple tasks to gpt-4o-mini",
            "description": (f"${cost:,.0f}/month on gpt-4o. Routing 60% of non-complex "
                            f"queries to gpt-4o-mini saves ~${savings:,.0f}/month."),
            "potential_savings_usd_month": savings,
            "effort": "low", "time_to_value_weeks": 1,
            "cloud": "azure", "team": r["team"],
        })

    # ── 2. Azure → OpenStack LLM migration ───────────────────────────────
    rows = await pool.fetch("""
        SELECT team, model_name, SUM(cost_usd) AS az_cost
        FROM ai_costs
        WHERE time >= NOW() - INTERVAL '30 days'
          AND cloud = 'azure' AND workload_type = 'llm_inference'
        GROUP BY team, model_name
        HAVING SUM(cost_usd) > 100
        ORDER BY az_cost DESC LIMIT 20
    """)
    for r in rows:
        az      = float(r["az_cost"])
        est_os  = az * 0.35
        savings = round(az - est_os, 2)
        recs.append({
            "id": f"migrate-{r['team']}-{r['model_name']}",
            "type": "CLOUD_MIGRATION",
            "priority": "high" if savings > 500 else "medium",
            "title": f"Migrate '{r['team']}' LLM inference to OpenStack vLLM",
            "description": (f"${az:,.0f}/month on Azure for {r['model_name']}. "
                            f"OpenStack equivalent estimated ${est_os:,.0f}. "
                            f"Potential saving: ${savings:,.0f}/month."),
            "potential_savings_usd_month": savings,
            "effort": "medium", "time_to_value_weeks": 4,
            "cloud_from": "azure", "cloud_to": "openstack",
            "team": r["team"], "model": r["model_name"],
        })

    # ── 3. GPU idle waste (both clouds) ──────────────────────────────────
    rows = await pool.fetch("""
        SELECT cloud, team, gpu_type,
               AVG(gpu_util_pct) AS avg_util,
               SUM(cost_usd)     AS cost
        FROM ai_costs
        WHERE time >= NOW() - INTERVAL '7 days'
          AND gpu_hours > 0 AND gpu_util_pct IS NOT NULL
        GROUP BY cloud, team, gpu_type
        HAVING AVG(gpu_util_pct) < 30
    """)
    for r in rows:
        cost  = float(r["cost"])
        util  = float(r["avg_util"] or 0)
        waste = round(cost * (1 - util / 100) * 4, 2)
        action = "scale-to-zero via HPA" if r["cloud"] == "azure" else "hibernate Nova instance"
        recs.append({
            "id": f"gpu-idle-{r['team']}-{r['cloud']}",
            "type": "GPU_OPTIMISATION",
            "priority": "high" if waste > 200 else "low",
            "title": f"Idle {r['gpu_type']} on {r['cloud']} ({util:.0f}% avg utilisation)",
            "description": (f"~${waste:,.0f}/month wasted. Recommended action: {action}."),
            "potential_savings_usd_month": waste,
            "effort": "low", "time_to_value_weeks": 1,
            "cloud": r["cloud"], "team": r["team"],
        })

    # ── 4. Agent loop guardrails ──────────────────────────────────────────
    rows = await pool.fetch("""
        SELECT cloud, team, COUNT(*) AS sessions, SUM(cost_usd) AS cost
        FROM ai_costs
        WHERE time >= NOW() - INTERVAL '7 days'
          AND tool_calls > 30 AND agent_session_id IS NOT NULL
        GROUP BY cloud, team
    """)
    for r in rows:
        cost    = float(r["cost"])
        savings = round(cost * 4 * 0.6, 2)
        recs.append({
            "id": f"agent-{r['team']}-{r['cloud']}",
            "type": "AGENT_GUARDRAIL",
            "priority": "high",
            "title": f"Add agent guardrails for '{r['team']}' on {r['cloud']}",
            "description": (f"{r['sessions']} runaway sessions (${cost:,.0f} this week). "
                            f"A $5/session cap + 50 tool-call limit eliminates loop explosions."),
            "potential_savings_usd_month": savings,
            "effort": "low", "time_to_value_weeks": 1,
            "cloud": r["cloud"], "team": r["team"],
        })

    # ── 5. Semantic cache opportunity ────────────────────────────────────
    rows = await pool.fetch("""
        SELECT cloud, team, SUM(cost_usd) AS cost,
               SUM(cached_tokens) AS cached, SUM(prompt_tokens) AS prompt
        FROM ai_costs
        WHERE time >= NOW() - INTERVAL '30 days'
          AND workload_type = 'llm_inference'
        GROUP BY cloud, team
        HAVING SUM(prompt_tokens) > 100000 AND SUM(cached_tokens) / NULLIF(SUM(prompt_tokens),0) < 0.1
    """)
    for r in rows:
        cost    = float(r["cost"])
        savings = round(cost * 0.30, 2)  # 30% from 40% cache hit rate
        recs.append({
            "id": f"cache-{r['team']}-{r['cloud']}",
            "type": "SEMANTIC_CACHE",
            "priority": "medium",
            "title": f"Enable semantic caching for '{r['team']}' on {r['cloud']}",
            "description": (f"Current cache hit rate <10%. A 40% hit rate target "
                            f"would save ~${savings:,.0f}/month on ${cost:,.0f} spend."),
            "potential_savings_usd_month": savings,
            "effort": "low", "time_to_value_weeks": 2,
            "cloud": r["cloud"], "team": r["team"],
        })

    recs.sort(key=lambda x: x.get("potential_savings_usd_month", 0), reverse=True)
    total = round(sum(r.get("potential_savings_usd_month", 0) for r in recs), 2)
    return {
        "recommendations": recs,
        "total_count": len(recs),
        "total_potential_savings_usd_month": total,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "recommendation-svc"}
