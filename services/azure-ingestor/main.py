"""
Azure AI Cost Ingestor — FastAPI service
Polls: Azure Cost Management API, Azure Monitor, AI Foundry, Azure ML
Emits: UnifiedCostEvent objects to Kafka topics azure.*
"""
import os, orjson
from fastapi import FastAPI
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import QueryDefinition, QueryTimePeriod, GranularityType
from azure.monitor.query import MetricsQueryClient
from azure.ai.projects import AIProjectClient
from aiokafka import AIOKafkaProducer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone
import sys; sys.path.insert(0, "/app")
from models.cost_event import UnifiedCostEvent

app       = FastAPI(title="Azure AI Cost Ingestor", version="2.0")
cred      = DefaultAzureCredential()
scheduler = AsyncIOScheduler()

AZURE_PRICES = {
    "gpt-4o":              {"input": 0.0025,  "output": 0.0100},
    "gpt-4o-mini":         {"input": 0.000150,"output": 0.000600},
    "gpt-4":               {"input": 0.030,   "output": 0.060},
    "text-embedding-3-small":{"input":0.00002, "output": 0.0},
    "text-embedding-3-large":{"input":0.00013, "output": 0.0},
    "o3-mini":             {"input": 0.0011,  "output": 0.0044},
}

AZURE_GPU_RATES = {
    "Standard_NC24ads_A100_v4": 3.673,
    "Standard_ND96amsr_A100_v4": 6.12,
    "Standard_NC6s_v3":  0.902,
    "Standard_NV36ads_A10_v5": 1.10,
}


class AzureIngestor:
    def __init__(self):
        self.sub_id   = os.environ["AZURE_SUBSCRIPTION_ID"]
        self.cost_mgr = CostManagementClient(cred, self.sub_id)
        self.metrics  = MetricsQueryClient(cred)
        self.foundry  = AIProjectClient(
            endpoint=os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", ""),
            credential=cred)
        self.producer = AIOKafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
            value_serializer=lambda v: orjson.dumps(v))

    async def ingest_openai_metrics(self):
        """Poll Azure Monitor for per-deployment token counts (5-min lag)."""
        async for resource in self._list_openai_resources():
            try:
                m = await self._get_token_metrics(resource.id)
                if not m.get("TotalTokens"):
                    continue
                rates = AZURE_PRICES.get(m.get("deployment_name", ""), {"input": 0, "output": 0})
                cost  = (m.get("PromptTokens", 0) / 1000 * rates["input"] +
                         m.get("CompletionTokens", 0) / 1000 * rates["output"])
                event = UnifiedCostEvent(
                    cloud="azure",        workload_type="llm_inference",
                    tenant_id=self.sub_id, region=resource.location,
                    team=resource.tags.get("team", "untagged"),
                    feature=resource.tags.get("feature", "unknown"),
                    env=resource.tags.get("env", "dev"),
                    cost_centre=resource.tags.get("cost-centre", "untagged"),
                    resource_id=resource.id, resource_type="azure-openai",
                    model_name=m.get("deployment_name"),
                    prompt_tokens=m.get("PromptTokens", 0),
                    completion_tokens=m.get("CompletionTokens", 0),
                    cost_usd=cost, unit_rate_usd=rates["input"],
                    billing_model="payg",
                )
                await self.producer.send("azure.openai.usage",
                                         event.model_dump(mode="json"))
            except Exception as e:
                print(f"[azure-ingestor] ERROR processing {resource.id}: {e}")

    async def ingest_foundry_jobs(self):
        """Capture AI Foundry fine-tuning + eval run costs."""
        try:
            async for job in self.foundry.jobs.list(status_filter="Completed"):
                hours = getattr(job, "compute_hours", 0) or 0
                sku   = getattr(job, "cluster_sku", "Standard_NC6s_v3")
                rate  = AZURE_GPU_RATES.get(sku, 1.0)
                await self.producer.send("azure.foundry.jobs", {
                    "cloud": "azure",
                    "job_id": job.id, "job_type": job.type,
                    "compute_hours": hours,
                    "model": getattr(getattr(job, "fine_tune_details", None), "model", None),
                    "cost_usd": hours * rate,
                    "sku": sku,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            print(f"[azure-ingestor] Foundry error: {e}")

    async def ingest_billing_daily(self):
        """Pull Azure Cost Management daily rollup for full resource coverage."""
        end   = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
        scope = f"/subscriptions/{self.sub_id}"
        try:
            result = self.cost_mgr.query.usage(scope, QueryDefinition(
                type="ActualCost",
                timeframe="Custom",
                time_period=QueryTimePeriod(from_property=start, to=end),
                granularity=GranularityType.DAILY,
                grouping=[{"type": "Dimension", "name": "ResourceType"},
                          {"type": "TagKey",    "name": "team"},
                          {"type": "TagKey",    "name": "feature"}],
            ))
            for row in (result.rows or []):
                await self.producer.send("azure.billing.daily", {
                    "cloud": "azure", "date": start.date().isoformat(),
                    "resource_type": row[2], "team": row[3],
                    "feature": row[4], "cost_usd": float(row[0]),
                })
        except Exception as e:
            print(f"[azure-ingestor] Billing error: {e}")

    # ── private helpers ─────────────────────────────────────────────────
    async def _list_openai_resources(self):
        from azure.mgmt.resource import ResourceManagementClient
        rm = ResourceManagementClient(cred, self.sub_id)
        for r in rm.resources.list(filter="resourceType eq 'Microsoft.CognitiveServices/accounts'"):
            yield r

    async def _get_token_metrics(self, resource_id: str) -> dict:
        from azure.monitor.query import MetricAggregationType
        from datetime import timedelta
        result = self.metrics.query_resource(
            resource_id,
            metric_names=["PromptTokensUsed", "CompletionTokensUsed", "TotalTokensUsed"],
            timespan=timedelta(minutes=10),
            granularity=timedelta(minutes=5),
            aggregations=[MetricAggregationType.TOTAL],
        )
        out = {}
        for m in result.metrics:
            for ts in m.timeseries:
                for dp in ts.data:
                    if dp.total:
                        out[m.name] = int(dp.total)
        return out


ingestor = AzureIngestor()

@app.on_event("startup")
async def startup():
    await ingestor.producer.start()
    scheduler.add_job(ingestor.ingest_openai_metrics, "interval", minutes=5,  id="openai")
    scheduler.add_job(ingestor.ingest_foundry_jobs,   "interval", hours=1,    id="foundry")
    scheduler.add_job(ingestor.ingest_billing_daily,  "interval", hours=24,   id="billing",
                      next_run_time=datetime.now(timezone.utc).replace(hour=2, minute=0))
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    await ingestor.producer.stop()
    scheduler.shutdown()

@app.get("/health")
async def health():
    return {"status": "ok", "service": "azure-ingestor", "cloud": "azure"}

@app.post("/trigger/{job}")
async def trigger(job: str):
    """Manual trigger for any ingestor job (dev/debug)."""
    if job == "openai":   await ingestor.ingest_openai_metrics()
    elif job == "foundry": await ingestor.ingest_foundry_jobs()
    elif job == "billing": await ingestor.ingest_billing_daily()
    else: return {"error": f"Unknown job: {job}"}
    return {"triggered": job}
