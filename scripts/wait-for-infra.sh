#!/bin/bash
# Wait for all infrastructure services to be healthy before starting microservices
set -e
echo "⏳ Waiting for infrastructure..."

wait_for() {
  local name=$1; local host=$2; local port=$3; local max=${4:-60}
  local i=0
  while ! nc -z "$host" "$port" 2>/dev/null; do
    i=$((i+1)); [ $i -ge $max ] && echo "❌ Timeout: $name" && exit 1
    echo "  Waiting for $name ($i/$max)..."; sleep 2
  done
  echo "  ✅ $name ready"
}

wait_for "Kafka"       kafka       9092
wait_for "TimescaleDB" timescaledb 5432
wait_for "ClickHouse"  clickhouse  8123
wait_for "Redis"       redis       6379

echo "🚀 All infrastructure ready!"
