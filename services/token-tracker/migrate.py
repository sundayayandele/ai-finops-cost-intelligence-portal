"""Run database migrations — TimescaleDB hypertable + ClickHouse table."""
import asyncio, asyncpg, os, clickhouse_connect

TIMESCALE_SQL = """
CREATE TABLE IF NOT EXISTS ai_costs (
    time              TIMESTAMPTZ       NOT NULL,
    cloud             TEXT              NOT NULL,
    workload_type     TEXT              NOT NULL,
    tenant_id         TEXT              NOT NULL,
    team              TEXT              NOT NULL DEFAULT 'untagged',
    feature           TEXT,
    env               TEXT,
    cost_centre       TEXT,
    resource_id       TEXT,
    resource_type     TEXT,
    model_name        TEXT,
    prompt_tokens     BIGINT            DEFAULT 0,
    completion_tokens BIGINT            DEFAULT 0,
    cached_tokens     BIGINT            DEFAULT 0,
    total_tokens      BIGINT            DEFAULT 0,
    gpu_hours         DOUBLE PRECISION  DEFAULT 0.0,
    cpu_hours         DOUBLE PRECISION  DEFAULT 0.0,
    gpu_type          TEXT,
    gpu_util_pct      DOUBLE PRECISION,
    cost_usd          DOUBLE PRECISION  NOT NULL,
    unit_rate_usd     DOUBLE PRECISION  DEFAULT 0.0,
    billing_model     TEXT              NOT NULL,
    agent_session_id  TEXT,
    tool_calls        INT               DEFAULT 0,
    context_tokens    INT               DEFAULT 0
);

SELECT create_hypertable('ai_costs','time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ai_costs_cloud       ON ai_costs(cloud, time DESC);
CREATE INDEX IF NOT EXISTS idx_ai_costs_team        ON ai_costs(team, time DESC);
CREATE INDEX IF NOT EXISTS idx_ai_costs_model       ON ai_costs(model_name, time DESC);
CREATE INDEX IF NOT EXISTS idx_ai_costs_agent       ON ai_costs(agent_session_id) WHERE agent_session_id IS NOT NULL;

-- Continuous aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS costs_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    cloud, workload_type, team, model_name,
    SUM(cost_usd)          AS total_cost,
    SUM(prompt_tokens)     AS total_prompt_tokens,
    SUM(completion_tokens) AS total_completion_tokens,
    SUM(cached_tokens)     AS total_cached_tokens,
    SUM(gpu_hours)         AS total_gpu_hours,
    COUNT(*)               AS event_count
FROM ai_costs
GROUP BY 1,2,3,4,5
WITH NO DATA;

SELECT add_continuous_aggregate_policy('costs_1h',
    start_offset => INTERVAL '4 hours',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

CREATE MATERIALIZED VIEW IF NOT EXISTS costs_1d
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    cloud, workload_type, team, model_name,
    SUM(cost_usd)   AS total_cost,
    SUM(gpu_hours)  AS total_gpu_hours,
    COUNT(*)        AS event_count
FROM ai_costs
GROUP BY 1,2,3,4,5
WITH NO DATA;
"""

CLICKHOUSE_SQL = """
CREATE DATABASE IF NOT EXISTS ai_finops;

CREATE TABLE IF NOT EXISTS ai_finops.ai_cost_events (
    event_id         UUID,
    cloud            LowCardinality(String),
    workload_type    LowCardinality(String),
    tenant_id        String,
    team             LowCardinality(String),
    feature          String,
    env              LowCardinality(String),
    model            LowCardinality(String),
    prompt_tokens    UInt64,
    completion_tokens UInt64,
    cached_tokens    UInt64,
    gpu_hours        Float64,
    cost_usd         Float64,
    billing_model    LowCardinality(String),
    agent_session_id String,
    tool_calls       UInt32,
    ts               DateTime64(3,'UTC')
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(ts)
ORDER BY (cloud, team, model, ts);
"""

async def run_timescale():
    conn = await asyncpg.connect(os.environ["TIMESCALE_DSN"])
    await conn.execute(TIMESCALE_SQL)
    await conn.close()
    print("TimescaleDB migrations applied.")

def run_clickhouse():
    ch = clickhouse_connect.get_client(host=os.getenv("CLICKHOUSE_HOST","clickhouse"))
    for stmt in CLICKHOUSE_SQL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            ch.command(stmt)
    print("ClickHouse migrations applied.")

if __name__ == "__main__":
    asyncio.run(run_timescale())
    run_clickhouse()
