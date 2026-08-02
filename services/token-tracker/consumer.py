"""
Token Cost Consumer — aiokafka consumer
Consumes from all cloud topics, calculates token costs, writes to TimescaleDB + ClickHouse.
"""
import os, orjson, asyncio
from aiokafka import AIOKafkaConsumer
import asyncpg, clickhouse_connect
import tiktoken
from transformers import AutoTokenizer
import sys; sys.path.insert(0, "/app")
from models.cost_event import UnifiedCostEvent

TOPICS = [
    "azure.openai.usage", "azure.foundry.jobs", "azure.billing.daily",
    "openstack.vllm.usage", "openstack.nova.gpu", "openstack.ceilometer.samples",
    "ai.costs.unified",
]

TIKTOKEN_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4", "o3-mini",
                   "text-embedding-3-small", "text-embedding-3-large"}


class TokenCostConsumer:
    def __init__(self):
        self.ts_pool  = None
        self.ch       = None
        self._hf_cache: dict = {}

    async def run(self):
        self.ts_pool = await asyncpg.create_pool(
            dsn=os.environ["TIMESCALE_DSN"], min_size=2, max_size=10)
        self.ch = clickhouse_connect.get_client(
            host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            database="ai_finops",
        )
        consumer = AIOKafkaConsumer(
            *TOPICS,
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
            group_id="token-tracker-v2",
            auto_offset_reset="earliest",
            value_deserializer=lambda b: orjson.loads(b),
        )
        await consumer.start()
        print("[token-tracker] Listening…")
        try:
            async for msg in consumer:
                await self._process(msg.topic, msg.value)
        finally:
            await consumer.stop()
            await self.ts_pool.close()

    async def _process(self, topic: str, raw: dict):
        try:
            event = UnifiedCostEvent(**raw)
        except Exception as e:
            print(f"[token-tracker] Schema error {topic}: {e}")
            return
        await self._write_timescale(event)
        self._write_clickhouse(event)

    async def _write_timescale(self, e: UnifiedCostEvent):
        await self.ts_pool.execute("""
            INSERT INTO ai_costs (
                time, cloud, workload_type, tenant_id, team, feature, env,
                cost_centre, resource_id, resource_type, model_name,
                prompt_tokens, completion_tokens, cached_tokens, total_tokens,
                gpu_hours, cpu_hours, gpu_type, gpu_util_pct,
                cost_usd, unit_rate_usd, billing_model,
                agent_session_id, tool_calls, context_tokens
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                $16,$17,$18,$19,$20,$21,$22,$23,$24,$25
            ) ON CONFLICT DO NOTHING
        """,
            e.timestamp, str(e.cloud), str(e.workload_type),
            e.tenant_id, e.team, e.feature, e.env,
            e.cost_centre, e.resource_id, e.resource_type, e.model_name,
            e.prompt_tokens, e.completion_tokens, e.cached_tokens, e.total_tokens,
            e.gpu_hours, e.cpu_hours, e.gpu_type, e.gpu_util_pct,
            e.cost_usd, e.unit_rate_usd, e.billing_model,
            e.agent_session_id, e.tool_calls, e.context_tokens,
        )

    def _write_clickhouse(self, e: UnifiedCostEvent):
        try:
            self.ch.insert("ai_cost_events", [[
                str(e.event_id), str(e.cloud), str(e.workload_type),
                e.tenant_id, e.team, e.feature, e.env, e.model_name or "",
                e.prompt_tokens, e.completion_tokens, e.cached_tokens,
                e.gpu_hours, e.cost_usd, e.billing_model,
                e.agent_session_id or "", e.tool_calls, e.timestamp,
            ]], column_names=[
                "event_id","cloud","workload_type","tenant_id","team","feature","env","model",
                "prompt_tokens","completion_tokens","cached_tokens",
                "gpu_hours","cost_usd","billing_model",
                "agent_session_id","tool_calls","ts",
            ])
        except Exception as ex:
            print(f"[token-tracker] ClickHouse error: {ex}")


if __name__ == "__main__":
    asyncio.run(TokenCostConsumer().run())
