#!/bin/bash
# Start all services in development mode (hot reload)
set -e
echo "🚀 Starting AI FinOps Platform (dev mode)"

# Start infra first
docker-compose up -d kafka timescaledb clickhouse redis
./scripts/wait-for-infra.sh

# Run migrations
cd services/token-tracker && python scripts/migrate.py && cd ../..

# Create Kafka topics
./scripts/create-kafka-topics.sh

# Start services in background
for svc in cost-normaliser token-tracker anomaly-detector; do
  echo "Starting $svc..."
  (cd services/$svc && uvicorn main:app --reload --port $(grep $svc ports.txt | cut -d: -f2)) &
done

echo "✅ Platform started. Frontend: npm run dev in ./frontend"
