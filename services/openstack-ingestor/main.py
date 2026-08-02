"""
OpenStack AI Cost Ingestor — FastAPI service
Integrates: Ceilometer metering, Gnocchi metrics, Nova GPU, vLLM Prometheus
Emits: UnifiedCostEvent objects to Kafka topics openstack.*
"""
import os, orjson, asyncio, re
from fastapi import FastAPI
import openstack, httpx
from aiokafka import AIOKafkaProducer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from typing import Optional
import sys; sys.path.insert(0, "/app")
from models.cost_event import UnifiedCostEvent

app       = FastAPI(title="OpenStack AI Cost Ingestor", version="2.0")
scheduler = AsyncIOScheduler()

# ── Load internal billing rates from env (CapEx amortised) ──────────────
OS_GPU_RATES = {
    "A100-80GB": float(os.getenv("OS_RATE_A100_80GB", "1.85")),
    "A100-40GB": float(os.getenv("OS_RATE_A100_40GB", "1.20")),
    "V100-16GB": float(os.getenv("OS_RATE_V100",      "0.45")),
    "H100-80GB": float(os.getenv("OS_RATE_H100",      "3.20")),
    "T4-16GB":   float(os.getenv("OS_RATE_T4",        "0.18")),
}
OS_VLLM_RATES = {   # per 1K tokens, input / output
    "llama-3-70b":   {"in": 0.0003, "out": 0.0006},
    "mistral-7b":    {"in": 0.00005,"out": 0.0001},
    "mixtral-8x7b":  {"in": 0.00015,"out": 0.0003},
    "deepseek-r1":   {"in": 0.0002, "out": 0.0004},
}

GPU_FLAVOR_MAP = {
    "gpu.a100.80gb": "A100-80GB",
    "gpu.v100.16gb": "V100-16GB",
    "gpu.h100.80gb": "H100-80GB",
    "gpu.t4.16gb":   "T4-16GB",
}


class OpenStackIngestor:
    def __init__(self):
        self.conn = openstack.connect(
            auth_url=os.environ["OS_AUTH_URL"],
            username=os.environ["OS_USERNAME"],
            password=os.environ["OS_PASSWORD"],
            project_name=os.getenv("OS_PROJECT_NAME", "ai-finops"),
            user_domain_id="default",
            project_domain_id="default",
        )
        self.gnocchi_url   = os.getenv("GNOCCHI_URL", "http://gnocchi:8041")
        self.vllm_urls     = os.getenv("VLLM_METRICS_URLS", "").split(",")
        self.region        = os.getenv("OS_REGION_NAME", "RegionOne")
        self.producer      = AIOKafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
            value_serializer=lambda v: orjson.dumps(v))

    # ── vLLM Prometheus scraping ──────────────────────────────────────────
    async def ingest_vllm_tokens(self):
        """Scrape all vLLM /metrics endpoints and emit per-model cost events."""
        async with httpx.AsyncClient(timeout=10) as client:
            for url in self.vllm_urls:
                url = url.strip()
                if not url:
                    continue
                try:
                    resp  = await client.get(url)
                    prom  = self._parse_prometheus(resp.text)

                    model_name     = prom.get("vllm:model_name", "unknown")
                    prompt_tokens  = int(float(prom.get("vllm:prompt_tokens_total", 0)))
                    gen_tokens     = int(float(prom.get("vllm:generation_tokens_total", 0)))
                    cached_tokens  = int(float(prom.get("vllm:cache_hit_tokens_total", 0)))

                    rates = OS_VLLM_RATES.get(model_name, {"in": 0.0003, "out": 0.0006})
                    cost  = (prompt_tokens / 1000 * rates["in"] +
                             gen_tokens   / 1000 * rates["out"])

                    project_id   = os.getenv("OS_PROJECT_ID", "unknown")
                    event = UnifiedCostEvent(
                        cloud="openstack", workload_type="llm_inference",
                        tenant_id=project_id, region=self.region,
                        team=self._project_tag("team"),
                        feature=self._project_tag("feature"),
                        env=self._project_tag("env"),
                        cost_centre=self._project_tag("cost-centre"),
                        resource_id=url, resource_type="vllm-endpoint",
                        model_name=model_name,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=gen_tokens,
                        cached_tokens=cached_tokens,
                        cost_usd=cost,
                        billing_model="internal",
                    )
                    await self.producer.send("openstack.vllm.usage",
                                             event.model_dump(mode="json"))
                except Exception as e:
                    print(f"[openstack-ingestor] vLLM error {url}: {e}")

    # ── Nova GPU instance metering ─────────────────────────────────────────
    async def ingest_gpu_instances(self):
        """Enumerate Nova GPU instances across all projects and emit cost events."""
        try:
            projects = list(self.conn.identity.projects())
        except Exception as e:
            print(f"[openstack-ingestor] Identity error: {e}")
            return

        for project in projects:
            try:
                servers = list(self.conn.compute.servers(
                    project_id=project.id, all_tenants=True))
                for server in servers:
                    flavor_name = server.flavor.get("original_name", "")
                    gpu_type    = GPU_FLAVOR_MAP.get(flavor_name)
                    if not gpu_type:
                        continue
                    hours   = self._runtime_hours(server)
                    rate    = OS_GPU_RATES.get(gpu_type, 1.0)
                    cost    = hours * rate
                    await self.producer.send("openstack.nova.gpu",
                        UnifiedCostEvent(
                            cloud="openstack", workload_type="gpu_compute",
                            tenant_id=project.id,
                            region=server.availability_zone or self.region,
                            team=server.metadata.get("team", "untagged"),
                            feature=server.metadata.get("feature", "unknown"),
                            env=server.metadata.get("env", "dev"),
                            cost_centre=server.metadata.get("cost-centre", "untagged"),
                            resource_id=server.id,
                            resource_type="nova-gpu-instance",
                            gpu_type=gpu_type,
                            gpu_hours=round(hours, 4),
                            cost_usd=round(cost, 6),
                            unit_rate_usd=rate,
                            billing_model="internal",
                        ).model_dump(mode="json"))
            except Exception as e:
                print(f"[openstack-ingestor] Project {project.id} error: {e}")

    # ── Ceilometer / Gnocchi samples ──────────────────────────────────────
    async def ingest_ceilometer_samples(self):
        """Pull aggregated resource metrics from Gnocchi REST API."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                r = await client.get(f"{self.gnocchi_url}/v1/metric",
                                     params={"limit": 200})
                for metric in r.json():
                    if metric.get("name") not in ("cpu_util", "memory.usage"):
                        continue
                    await self.producer.send("openstack.ceilometer.samples", {
                        "cloud": "openstack",
                        "metric_id": metric["id"],
                        "metric_name": metric["name"],
                        "resource_id": metric.get("resource_id"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception as e:
                print(f"[openstack-ingestor] Gnocchi error: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────
    def _parse_prometheus(self, text: str) -> dict:
        out = {}
        for line in text.splitlines():
            if line.startswith("#"):
                continue
            m = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\{?([^}]*)\}?\s+([0-9.e+\-]+)', line)
            if m:
                out[m.group(1)] = m.group(3)
                for kv in re.findall(r'(\w+)="([^"]+)"', m.group(2)):
                    if kv[0] == "model_name":
                        out["vllm:model_name"] = kv[1]
        return out

    def _runtime_hours(self, server) -> float:
        launched = server.launched_at
        if not launched:
            return 0.0
        if isinstance(launched, str):
            launched = datetime.fromisoformat(launched.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - launched).total_seconds() / 3600

    def _project_tag(self, key: str) -> str:
        return os.getenv(f"OS_TAG_{key.upper().replace('-','_')}", "unknown")


ingestor = OpenStackIngestor()

@app.on_event("startup")
async def startup():
    await ingestor.producer.start()
    scheduler.add_job(ingestor.ingest_vllm_tokens,        "interval", minutes=5, id="vllm")
    scheduler.add_job(ingestor.ingest_gpu_instances,      "interval", minutes=5, id="gpu")
    scheduler.add_job(ingestor.ingest_ceilometer_samples, "interval", minutes=15,id="ceilometer")
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    await ingestor.producer.stop()
    scheduler.shutdown()

@app.get("/health")
async def health():
    return {"status": "ok", "service": "openstack-ingestor", "cloud": "openstack"}
