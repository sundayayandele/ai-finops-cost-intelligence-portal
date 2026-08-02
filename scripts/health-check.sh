#!/bin/bash
# Check health of all 12 microservices
echo "🔍 AI FinOps Platform Health Check"
echo "─────────────────────────────────────"

check() {
  local name=$1; local url=$2
  if curl -sf "$url" > /dev/null 2>&1; then
    echo "  ✅ $name"
  else
    echo "  ❌ $name ($url)"
  fi
}

check "api-bff            :8000" "http://localhost:8000/health"
check "azure-ingestor     :8001" "http://localhost:8001/health"
check "openstack-ingestor :8002" "http://localhost:8002/health"
check "llm-gateway        :8010" "http://localhost:8010/health"
check "gpu-monitor        :8021" "http://localhost:8021/health"
check "forecast-engine    :8024" "http://localhost:8024/health"

echo "─────────────────────────────────────"
echo "Infrastructure:"
check "  Kafka"       "http://localhost:9092"  || true
check "  TimescaleDB" "http://localhost:5432"  || true
check "  ClickHouse"  "http://localhost:8123/ping"
check "  Redis"       "http://localhost:6379"  || true
check "  Frontend"    "http://localhost:5173"
