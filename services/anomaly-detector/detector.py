"""
Anomaly Detector — Kafka consumer + producer
Detects: cost spikes, agent loops, context bloat, GPU idle, cross-cloud routing opportunities
"""
import os, orjson, asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from collections import defaultdict, deque
from datetime import datetime, timezone
import statistics
import sys; sys.path.insert(0, "/app")
from models.cost_event import UnifiedCostEvent

ANOMALY_RULES = {
    "agent_loop":    {"tool_calls_threshold": 50},
    "context_bloat": {"context_tokens_threshold": 80_000},
    "gpu_idle":      {"util_threshold_pct": 10.0},
    "cost_spike":    {"z_score_threshold": 3.0, "window_size": 168},  # 7d hourly
    "routing_opportunity": {"azure_vs_os_ratio": 1.4},
}


class AnomalyDetector:
    def __init__(self):
        self._cost_windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=168))
        self.consumer = AIOKafkaConsumer(
            "ai.costs.unified",
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
            group_id="anomaly-detector-v2",
            value_deserializer=lambda b: orjson.loads(b),
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
            value_serializer=lambda v: orjson.dumps(v),
        )

    async def run(self):
        await self.consumer.start()
        await self.producer.start()
        print("[anomaly-detector] Monitoring unified cost stream…")
        try:
            async for msg in self.consumer:
                try:
                    event = UnifiedCostEvent(**msg.value)
                    anomalies = self._detect_all(event)
                    for a in anomalies:
                        await self.producer.send("ai.anomalies", a)
                except Exception as e:
                    print(f"[anomaly-detector] Error: {e}")
        finally:
            await self.consumer.stop()
            await self.producer.stop()

    def _detect_all(self, e: UnifiedCostEvent) -> list[dict]:
        anomalies = []
        anomalies.extend(self._check_agent_loop(e))
        anomalies.extend(self._check_context_bloat(e))
        anomalies.extend(self._check_cost_spike(e))
        anomalies.extend(self._check_gpu_idle(e))
        return anomalies

    def _check_agent_loop(self, e: UnifiedCostEvent) -> list:
        threshold = ANOMALY_RULES["agent_loop"]["tool_calls_threshold"]
        if e.tool_calls and e.tool_calls > threshold:
            return [self._anomaly(e, "AGENT_LOOP",
                f"Agent session {e.agent_session_id} has {e.tool_calls} tool calls (limit: {threshold})",
                severity="critical", action="kill_session")]
        return []

    def _check_context_bloat(self, e: UnifiedCostEvent) -> list:
        threshold = ANOMALY_RULES["context_bloat"]["context_tokens_threshold"]
        if e.context_tokens > threshold:
            return [self._anomaly(e, "CONTEXT_BLOAT",
                f"Context tokens {e.context_tokens:,} exceeds {threshold:,}",
                severity="warning", action="compress_prompt")]
        return []

    def _check_cost_spike(self, e: UnifiedCostEvent) -> list:
        key  = f"{e.cloud}:{e.team}:{e.model_name or 'all'}"
        window = self._cost_windows[key]
        window.append(e.cost_usd)
        if len(window) < 24:  # Need at least 24 data points
            return []
        try:
            mean   = statistics.mean(window)
            stdev  = statistics.stdev(window)
            if stdev == 0:
                return []
            z_score = (e.cost_usd - mean) / stdev
            threshold = ANOMALY_RULES["cost_spike"]["z_score_threshold"]
            if z_score > threshold:
                return [self._anomaly(e, "COST_SPIKE",
                    f"Z-score {z_score:.1f}σ — cost ${e.cost_usd:.4f} vs avg ${mean:.4f}",
                    severity="high", action="alert_team",
                    metadata={"z_score": round(z_score, 2), "mean": round(mean, 4)})]
        except Exception:
            pass
        return []

    def _check_gpu_idle(self, e: UnifiedCostEvent) -> list:
        if e.gpu_util_pct is None:
            return []
        threshold = ANOMALY_RULES["gpu_idle"]["util_threshold_pct"]
        if e.gpu_util_pct < threshold and e.gpu_hours > 0:
            waste = e.cost_usd * (1 - e.gpu_util_pct / 100)
            return [self._anomaly(e, "GPU_IDLE",
                f"GPU util {e.gpu_util_pct:.1f}% — wasting ~${waste:.4f}/hr",
                severity="warning", action="scale_to_zero" if e.cloud == "azure" else "hibernate")]
        return []

    def _anomaly(self, e: UnifiedCostEvent, type_: str, msg: str,
                 severity: str = "warning", action: str = "", metadata: dict = None) -> dict:
        return {
            "type": type_, "severity": severity, "message": msg,
            "cloud": str(e.cloud), "team": e.team, "model": e.model_name,
            "resource_id": e.resource_id, "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cost_usd": e.cost_usd, "metadata": metadata or {},
        }


if __name__ == "__main__":
    asyncio.run(AnomalyDetector().run())
