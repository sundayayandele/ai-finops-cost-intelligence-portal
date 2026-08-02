"""
Cost Normaliser — Kafka stream processor
Consumes raw events from azure.* and openstack.* topics
Enriches, validates, and emits UnifiedCostEvent to ai.costs.unified
"""
import os, orjson, asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import sys; sys.path.insert(0, "/app")
from models.cost_event import UnifiedCostEvent

SOURCE_TOPICS = [
    "azure.openai.usage", "azure.foundry.jobs", "azure.billing.daily", "azure.ml.compute",
    "openstack.vllm.usage", "openstack.nova.gpu", "openstack.ceilometer.samples",
]
UNIFIED_TOPIC = "ai.costs.unified"
DLQ_TOPIC     = "ai.costs.dlq"

REQUIRED_TAGS = {"team", "feature", "env", "cost_centre"}


class CostNormaliser:
    def __init__(self):
        self.consumer = AIOKafkaConsumer(
            *SOURCE_TOPICS,
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
            group_id="cost-normaliser-v2",
            auto_offset_reset="earliest",
            value_deserializer=lambda b: orjson.loads(b),
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
            value_serializer=lambda v: orjson.dumps(v),
        )
        self._tag_warnings: set = set()

    async def run(self):
        await self.consumer.start()
        await self.producer.start()
        print(f"[cost-normaliser] Consuming {SOURCE_TOPICS}")
        try:
            async for msg in self.consumer:
                normalised = await self._normalise(msg.topic, msg.value)
                if normalised:
                    await self.producer.send(UNIFIED_TOPIC, normalised.model_dump(mode="json"))
        finally:
            await self.consumer.stop()
            await self.producer.stop()

    async def _normalise(self, topic: str, raw: dict) -> UnifiedCostEvent | None:
        try:
            if "azure" in topic:
                raw = self._fill_azure_defaults(raw)
            else:
                raw = self._fill_openstack_defaults(raw)
            self._check_tags(topic, raw)
            return UnifiedCostEvent(**raw)
        except Exception as e:
            await self.producer.send(DLQ_TOPIC, {
                "topic": topic, "error": str(e), "raw": raw
            })
            return None

    def _fill_azure_defaults(self, raw: dict) -> dict:
        raw.setdefault("cloud", "azure")
        raw.setdefault("billing_model", "payg")
        raw.setdefault("team", "untagged")
        raw.setdefault("feature", "unknown")
        raw.setdefault("env", "dev")
        raw.setdefault("cost_centre", "untagged")
        raw.setdefault("region", "unknown")
        raw.setdefault("workload_type", "llm_inference")
        return raw

    def _fill_openstack_defaults(self, raw: dict) -> dict:
        raw.setdefault("cloud", "openstack")
        raw.setdefault("billing_model", "internal")
        # Map OpenStack metadata → unified tags
        meta = raw.pop("metadata", {}) or {}
        raw.setdefault("team",        meta.get("team", "untagged"))
        raw.setdefault("feature",     meta.get("feature", "unknown"))
        raw.setdefault("env",         meta.get("env", "dev"))
        raw.setdefault("cost_centre", meta.get("cost-centre", "untagged"))
        raw.setdefault("region",      meta.get("region", "RegionOne"))
        raw.setdefault("workload_type", "llm_inference")
        return raw

    def _check_tags(self, topic: str, raw: dict):
        missing = {t for t in REQUIRED_TAGS if raw.get(t) in (None, "", "untagged", "unknown")}
        if missing and topic not in self._tag_warnings:
            print(f"[cost-normaliser] WARNING: topic {topic} missing tags: {missing}")
            self._tag_warnings.add(topic)


if __name__ == "__main__":
    asyncio.run(CostNormaliser().run())
