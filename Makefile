.PHONY: help dev build push-azure push-openstack deploy-azure deploy-openstack topics migrate health clean

REGISTRY_AZURE    ?= myacr.azurecr.io
REGISTRY_OS       ?= harbor.private.cloud/finops
TAG               ?= 2.0

help:
	@echo ""
	@echo "AI FinOps Portal — Available Commands"
	@echo "────────────────────────────────────────"
	@echo "  make dev              Start local dev stack (Docker Compose)"
	@echo "  make build            Build all Docker images"
	@echo "  make push-azure       Push images to Azure Container Registry"
	@echo "  make push-openstack   Push images to OpenStack Harbor registry"
	@echo "  make deploy-azure     Deploy to AKS via Helm"
	@echo "  make deploy-openstack Deploy to OpenStack Magnum via Helm"
	@echo "  make topics           Create all Kafka topics"
	@echo "  make migrate          Run TimescaleDB + ClickHouse migrations"
	@echo "  make health           Check health of all services"
	@echo "  make clean            Stop and remove all containers"
	@echo ""

dev:
	docker-compose up -d
	./scripts/wait-for-infra.sh
	@echo "✅ Platform running. Dashboard: http://localhost:5173"

build:
	docker-compose build

push-azure:
	./scripts/build-push-azure.sh $(REGISTRY_AZURE) $(TAG)

push-openstack:
	./scripts/build-push-openstack.sh $(REGISTRY_OS) $(TAG)

deploy-azure:
	helm upgrade --install ai-finops ./helm \
	  -f helm/values-azure.yaml \
	  --namespace ai-finops --create-namespace

deploy-openstack:
	helm upgrade --install ai-finops ./helm \
	  -f helm/values-openstack.yaml \
	  --namespace ai-finops --create-namespace

topics:
	./scripts/create-kafka-topics.sh

migrate:
	docker-compose run --rm token-tracker python migrate.py

health:
	./scripts/health-check.sh

clean:
	docker-compose down -v
	@echo "✅ All containers stopped and volumes removed."
