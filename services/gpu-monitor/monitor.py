"""
GPU Monitor — Prometheus DCGM scraper
Works identically for both AKS (Azure) and Magnum/k3s (OpenStack) nodes.
Uses the shared PrometheusGPUProvider with cloud-specific Prometheus URL.
"""
import os, asyncio, httpx, orjson
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiokafka import AIOKafkaProducer
from datetime import datetime, timezone

app       = FastAPI(title="GPU Monitor", version="2.0")
scheduler = AsyncIOScheduler()

GPU_RATES_USD_HR = {
    # Azure market rates
    "azure:A100-40GB": 3.673, "azure:A100-80GB": 6.12,
    "azure:V100":      0.902, "azure:T4":        0.526,
    "azure:H100":      6.98,
    # OpenStack CapEx amortised internal rates
    "openstack:A100-80GB": 1.85,
    "openstack:V100":      0.45,
    "openstack:H100":      3.20,
    "openstack:T4":        0.18,
}

DCGM_QUERIES = {
    "gpu_util":    'avg(DCGM_FI_DEV_GPU_UTIL) by (node, gpu, modelName)',
    "mem_util":    'avg(DCGM_FI_DEV_MEM_COPY_UTIL) by (node, gpu)',
    "power_usage": 'avg(DCGM_FI_DEV_POWER_USAGE) by (node, gpu)',
    "fb_used":     'avg(DCGM_FI_DEV_FB_USED) by (node, gpu)',
    "sm_active":   'avg(DCGM_FI_PROF_GR_ENGINE_ACTIVE) by (node, gpu)',
}


class PrometheusGPUProvider:
    """Works for both Azure AKS and OpenStack Magnum — same DCGM exporter."""
    def __init__(self, prometheus_url: str, cloud: str):
        self.prom  = prometheus_url
        self.cloud = cloud

    async def get_all_nodes(self) -> list[dict]:
        results = []
        async with httpx.AsyncClient(timeout=15) as client:
            util_resp = await client.get(f"{self.prom}/api/v1/query",
                                          params={"query": DCGM_QUERIES["gpu_util"]})
            for item in util_resp.json().get("data", {}).get("result", []):
                metric     = item["metric"]
                node       = metric.get("node", "unknown")
                gpu_idx    = metric.get("gpu", "0")
                gpu_model  = metric.get("modelName", "unknown").replace(" ", "-")
                util_pct   = float(item["value"][1])
                rate_key   = f"{self.cloud}:{gpu_model}"
                rate       = GPU_RATES_USD_HR.get(rate_key, 1.0)
                waste_hr   = rate * ((100 - util_pct) / 100)
                results.append({
                    "cloud": self.cloud, "node": node, "gpu": gpu_idx,
                    "gpu_model": gpu_model, "util_pct": round(util_pct, 2),
                    "rate_usd_hr": rate, "waste_usd_hr": round(waste_hr, 4),
                    "idle": util_pct < 10.0, "underused": util_pct < 60.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        return results


az_provider = PrometheusGPUProvider(
    os.getenv("AZURE_PROMETHEUS_URL", "http://prometheus-azure:9090"),
    "azure")
os_provider = PrometheusGPUProvider(
    os.getenv("OS_PROMETHEUS_URL", "http://prometheus-openstack:9090"),
    "openstack")
producer: AIOKafkaProducer = None


async def scrape_all():
    global producer
    for provider in [az_provider, os_provider]:
        try:
            nodes = await provider.get_all_nodes()
            for node in nodes:
                if node["idle"]:
                    await producer.send("ai.anomalies", {
                        "type": "GPU_IDLE",
                        "severity": "warning",
                        "cloud": node["cloud"],
                        "message": f"GPU idle {node['util_pct']}% on {node['node']}",
                        "action": "scale_to_zero" if node["cloud"] == "azure" else "hibernate",
                        "waste_usd_hr": node["waste_usd_hr"],
                        "timestamp": node["timestamp"],
                    })
        except Exception as e:
            print(f"[gpu-monitor] Scrape error {provider.cloud}: {e}")


@app.on_event("startup")
async def startup():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        value_serializer=lambda v: orjson.dumps(v))
    await producer.start()
    scheduler.add_job(scrape_all, "interval", minutes=5)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    await producer.stop()
    scheduler.shutdown()

@app.get("/api/v1/gpu/utilisation")
async def gpu_utilisation():
    az_nodes = await az_provider.get_all_nodes()
    os_nodes = await os_provider.get_all_nodes()
    return {"azure": az_nodes, "openstack": os_nodes,
            "total_idle": sum(1 for n in az_nodes + os_nodes if n["idle"]),
            "total_waste_usd_hr": round(sum(n["waste_usd_hr"] for n in az_nodes + os_nodes), 2)}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "gpu-monitor"}
