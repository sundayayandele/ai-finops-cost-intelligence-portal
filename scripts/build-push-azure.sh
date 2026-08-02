#!/bin/bash
# Build and push all Docker images to Azure Container Registry
set -e
REGISTRY=${1:-"myacr.azurecr.io"}
TAG=${2:-"2.0"}
echo "🔨 Building and pushing to $REGISTRY (tag: $TAG)"

az acr login --name "${REGISTRY%%.*}"

SERVICES=(azure-ingestor openstack-ingestor llm-gateway cost-normaliser
           token-tracker gpu-monitor anomaly-detector forecast-engine
           recommendation-svc api-bff)

for svc in "${SERVICES[@]}"; do
  echo "📦 Building $svc..."
  docker build -t "$REGISTRY/$svc:$TAG" "./services/$svc/" 2>/dev/null || \
    docker build -t "$REGISTRY/$svc:$TAG" -f "./services/$svc/Dockerfile" .
  docker push "$REGISTRY/$svc:$TAG"
  echo "  ✅ Pushed $REGISTRY/$svc:$TAG"
done

echo "🚀 Build and push complete for all services."
