#!/bin/bash
# Build and push all Docker images to OpenStack Harbor registry
set -e
REGISTRY=${1:-"harbor.private.cloud/finops"}
TAG=${2:-"2.0"}
echo "🔨 Building and pushing to $REGISTRY (tag: $TAG)"

docker login "$REGISTRY" -u "$HARBOR_USER" -p "$HARBOR_PASSWORD"

SERVICES=(azure-ingestor openstack-ingestor llm-gateway cost-normaliser
           token-tracker gpu-monitor anomaly-detector forecast-engine
           recommendation-svc api-bff)

for svc in "${SERVICES[@]}"; do
  echo "📦 Building $svc..."
  docker build -t "$REGISTRY/$svc:$TAG" "./services/$svc/"
  docker push "$REGISTRY/$svc:$TAG"
  echo "  ✅ Pushed $REGISTRY/$svc:$TAG"
done
echo "🚀 Build and push complete."
