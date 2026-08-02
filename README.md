# 🚀 AI FinOps Cost Intelligence Portal
### Dual-Cloud · Azure + OpenStack · Python + React

> **Production-grade AI workload cost tracking, optimisation, and forecasting across Azure OpenAI, AI Foundry, Azure ML, OpenStack vLLM/Ollama, Nova GPU compute, and Ceilometer metering — all in one platform.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)
![Azure](https://img.shields.io/badge/Azure-OpenAI%20%7C%20ML%20%7C%20Foundry-0078D4?logo=microsoftazure&logoColor=white)
![OpenStack](https://img.shields.io/badge/OpenStack-vLLM%20%7C%20Nova%20%7C%20Ceilometer-ED1944?logo=openstack&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache-Kafka-231F20?logo=apachekafka&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Microservices](#microservices)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Cost Optimisation Levers](#cost-optimisation-levers)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

---

## Overview

The **AI FinOps Cost Intelligence Portal** is a 12-microservice Python platform that unifies AI workload cost data from **Microsoft Azure** and **OpenStack private cloud** into a single real-time dashboard with forecasting, anomaly detection, and cross-cloud optimisation recommendations.

### Supported Workload Types

| Workload | Azure Sources | OpenStack Sources |
|----------|---------------|-------------------|
| LLM Inference | Azure OpenAI (GPT-4o, o3) | vLLM, Ollama, TGI |
| Agentic AI | AI Foundry Agent Sessions | OpenWebUI + vLLM |
| ML Training | Azure ML Compute Clusters | Nova GPU Instances |
| ML Inference | Azure ML Endpoints | Triton, Ray Serve |
| Embeddings | Azure OpenAI text-embedding-3 | sentence-transformers |
| Fine-tuning | AI Foundry fine-tune jobs | OpenStack + LoRA |
| GPU Compute | Azure NC/ND VM series | Nova flavors with GPU |

### Key Numbers
- **65% average cost reduction** achievable within 3 months
- **30-day forecasting** with 95% confidence intervals
- **< 5 min latency** from cost event to dashboard
- **Zero-downtime** deployment on both AKS and OpenStack Magnum

---

## Architecture

```
┌──────────────────────────┐          ┌──────────────────────────┐
│      AZURE CLOUD         │          │   OPENSTACK PRIVATE      │
│                          │          │                          │
│  Azure OpenAI ──────────┐│          │┌── vLLM / Ollama         │
│  AI Foundry  ──────────┐││          │├── Ceilometer Metering   │
│  Azure ML    ──────────┤││          │├── Gnocchi Metrics       │
│  Cognitive SVCs ───────┤││          │├── Nova GPU Compute      │
│  Cost Mgmt API ────────┤││          │├── Magnum K8s            │
│                         │││          │└── Heat Stacks           │
│  azure-ingestor ────────┘││          │                          │
│  (FastAPI :8001)  ───────┼┼──────────┼── openstack-ingestor    │
└──────────────────────────┘│          │   (FastAPI :8002) ───────┘
                             │          │          │
                    ┌────────▼──────────▼────────┐
                    │       Apache Kafka          │
                    │  azure.*  │  openstack.*   │
                    └─────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                       │
    ┌─────────▼────────┐  ┌────────▼────────┐  ┌─────────▼────────┐
    │ cost-normaliser  │  │  token-tracker  │  │ anomaly-detector │
    │ (aiokafka)       │  │  (tiktoken+HF)  │  │ (z-score+rules)  │
    └─────────┬────────┘  └────────┬────────┘  └─────────┬────────┘
              │                     │                       │
              └─────────────────────┼─────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  TimescaleDB         │
                         │  ClickHouse          │
                         │  Redis (cache)       │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │     FastAPI BFF :8000          │
                    │  REST + WebSocket API          │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │   React Dashboard (Vite)       │
                    │  Recharts + TanStack + Zustand │
                    └───────────────────────────────┘
```

---

## Microservices

| Service | Port | Cloud | Tech | Purpose |
|---------|------|-------|------|---------|
| `azure-ingestor` | 8001 | Azure | FastAPI + azure-sdk | Poll Azure Cost Mgmt + Monitor every 5 min |
| `openstack-ingestor` | 8002 | OpenStack | FastAPI + openstacksdk | Poll Ceilometer, Gnocchi, Nova GPU |
| `llm-gateway` | 8010 | Both | FastAPI + LiteLLM | Unified proxy: Azure OpenAI + vLLM/Ollama |
| `model-router` | 8011 | Both | FastAPI + RouteLLM | Cost/latency/policy routing between clouds |
| `semantic-cache` | 8012 | Both | FastAPI + GPTCache | Redis-backed cloud-agnostic LLM cache |
| `token-tracker` | 8020 | Both | aiokafka + tiktoken | Token counting → TimescaleDB + ClickHouse |
| `gpu-monitor` | 8021 | Both | Prometheus DCGM | GPU utilisation: Azure Monitor + DCGM |
| `cost-normaliser` | 8022 | Both | aiokafka | Enrich + validate → `ai.costs.unified` topic |
| `anomaly-detector` | 8023 | Both | aiokafka + scipy | Z-score + rules: spikes, loops, idle GPUs |
| `forecast-engine` | 8024 | Both | Prophet + LightGBM | 30d per-cloud + combined forecasting |
| `recommendation-svc` | 8025 | Both | FastAPI | Ranked savings + cross-cloud migration ROI |
| `api-bff` | 8000 | Both | FastAPI + asyncpg | REST + WebSocket BFF for React frontend |

---

## Quick Start

### Prerequisites

```bash
# Required
python >= 3.11
node >= 18
docker + docker-compose
kubectl + helm >= 3.12

# For Azure
az cli >= 2.50
# For OpenStack
openstack cli >= 6.0
```

### 1. Clone and configure

```bash
git clone https://github.com/sundayayandele/ai-finops-cost-intelligence-portal.git
cd ai-finops-cost-intelligence-portal

# Copy environment template
cp .env.example .env
# Edit .env with your Azure credentials + OpenStack credentials
```

### 2. Start infrastructure (local dev)

```bash
# Start Kafka, TimescaleDB, ClickHouse, Redis
docker-compose up -d kafka timescaledb clickhouse redis

# Wait for healthy state
./scripts/wait-for-infra.sh
```

### 3. Run database migrations

```bash
cd services/token-tracker
python scripts/migrate.py
```

### 4. Start all microservices

```bash
# Option A: Docker Compose (all services)
docker-compose up -d

# Option B: Individual services (dev)
./scripts/start-dev.sh
```

### 5. Start React frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 6. Verify platform health

```bash
./scripts/health-check.sh
# Checks all 12 microservices + Kafka + DBs
```

---

## Configuration

### Environment Variables

```bash
# ── Azure ─────────────────────────────────────────────
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id          # Service principal
AZURE_CLIENT_SECRET=your-client-secret  # Or use Managed Identity
AZURE_AI_FOUNDRY_ENDPOINT=https://your-foundry.api.azureml.ms

# ── OpenStack ─────────────────────────────────────────
OS_AUTH_URL=http://keystone:5000/v3
OS_USERNAME=finops-service-account
OS_PASSWORD=your-openstack-password
OS_PROJECT_NAME=ai-finops
OS_REGION_NAME=RegionOne
GNOCCHI_URL=http://gnocchi:8041
VLLM_METRICS_URL=http://vllm-service:8000/metrics
VLLM_BASE_URL=http://vllm-service:8000

# ── Infrastructure ─────────────────────────────────────
KAFKA_BOOTSTRAP=kafka:9092
TIMESCALE_DSN=postgresql://finops:pass@timescaledb:5432/ai_costs
CLICKHOUSE_HOST=clickhouse
REDIS_URL=redis://redis:6379

# ── OpenStack Billing Rates ($/GPU-hour, CapEx amortised)
OS_RATE_A100_80GB=1.85
OS_RATE_V100=0.45
OS_RATE_H100=3.20
OS_RATE_T4=0.18
```

### OpenStack Rate Configuration

Edit `config/openstack-rates.yaml` to set your organisation's CapEx amortised GPU rates:

```yaml
gpu_rates:
  A100-80GB: 1.85   # 3yr hardware amortisation + ops
  V100-16GB: 0.45
  H100-80GB: 3.20
  T4-16GB:   0.18

vllm_rates_per_1k_tokens:
  llama-3-70b:  { input: 0.0003, output: 0.0006 }
  mistral-7b:   { input: 0.00005, output: 0.0001 }
  mixtral-8x7b: { input: 0.00015, output: 0.0003 }
  deepseek-r1:  { input: 0.0002,  output: 0.0004 }
```

---

## Deployment

### Azure (AKS)

```bash
# 1. Build and push images to ACR
./scripts/build-push-azure.sh --registry myacr.azurecr.io --tag 2.0

# 2. Deploy with Helm
helm install ai-finops ./helm \
  -f helm/values-azure.yaml \
  --set cloud.subscriptionId=$AZURE_SUBSCRIPTION_ID \
  --namespace ai-finops --create-namespace

# 3. Verify
kubectl get pods -n ai-finops
```

### OpenStack (Magnum / k3s)

```bash
# 1. Build and push images to Harbor
./scripts/build-push-openstack.sh --registry harbor.private.cloud --tag 2.0

# 2. Deploy with Helm
helm install ai-finops ./helm \
  -f helm/values-openstack.yaml \
  --set cloud.authUrl=$OS_AUTH_URL \
  --namespace ai-finops --create-namespace

# 3. Verify
kubectl get pods -n ai-finops
```

### Dual-Cloud (Both simultaneously)

```bash
# Deploy to Azure cluster
KUBECONFIG=~/.kube/azure-config \
  helm install ai-finops-azure ./helm -f helm/values-azure.yaml

# Deploy to OpenStack cluster  
KUBECONFIG=~/.kube/openstack-config \
  helm install ai-finops-os ./helm -f helm/values-openstack.yaml
```

---

## Cost Optimisation Levers

| Lever | Cloud | Savings | Time-to-Value |
|-------|-------|---------|----------------|
| gpt-4o → gpt-4o-mini routing | Azure | 30–60% | 1–2 wks |
| Workload migration Azure → OpenStack vLLM | Both | 40–70% | 4–8 wks |
| Semantic caching (40% hit rate) | Both | 20–50% | 2–4 wks |
| Prompt compression (LLMLingua-2) | Both | 15–30% | 2–3 wks |
| GPU idle auto-shutdown | Both | 15–35% | 1 wk |
| OpenStack Spot/Preemptible GPU | OpenStack | 50–80% | 1–2 wks |
| Azure PTU Reservations | Azure | 20–40% | 4–8 wks |
| Agent loop guardrails | Both | 10–100% | 1 wk |
| MIG partitioning on A100 | Both | 40–60% | 2–4 wks |

**Combined target: $60,000–$75,000/month savings on $100K/month spend (3 months)**

---

## Project Structure

```
ai-finops-cost-intelligence-portal/
├── services/
│   ├── azure-ingestor/          # Azure Cost Mgmt + Monitor ingestor
│   ├── openstack-ingestor/      # Ceilometer + Gnocchi + Nova ingestor
│   ├── llm-gateway/             # LiteLLM unified proxy
│   ├── model-router/            # Cost/policy-based routing
│   ├── semantic-cache/          # GPTCache + Redis
│   ├── token-tracker/           # tiktoken + HuggingFace → TimescaleDB
│   ├── gpu-monitor/             # Prometheus DCGM scraper
│   ├── cost-normaliser/         # Kafka stream processor
│   ├── anomaly-detector/        # Z-score + rules engine
│   ├── forecast-engine/         # Prophet + LightGBM
│   ├── recommendation-svc/      # Savings ranking + migration ROI
│   └── api-bff/                 # FastAPI BFF: REST + WebSocket
├── frontend/                    # React 18 + TS + Recharts + shadcn/ui
├── models/                      # Shared Pydantic schemas
├── config/                      # Rates, routing rules, policies
├── helm/                        # Helm chart (values-azure + values-openstack)
├── k8s/                         # Raw Kubernetes manifests
├── scripts/                     # Dev, build, deploy, health-check scripts
├── docs/                        # Architecture diagrams, API docs
│   ├── dual-cloud-finops-guide.html   # Interactive build guide
│   └── dual-cloud-finops-guide.docx   # Word document reference
├── docker-compose.yml           # Local dev: all services + infra
├── docker-compose.infra.yml     # Infrastructure only (Kafka, DBs, Redis)
└── .env.example                 # Environment template
```

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/costs/summary?cloud=all\|azure\|openstack` | MTD cost summary |
| GET | `/api/v1/costs/timeseries` | Daily cost time-series |
| GET | `/api/v1/costs/by-cloud` | Azure vs OpenStack comparison |
| GET | `/api/v1/forecast/{cloud}/{horizon}` | Per-cloud forecast + CI |
| GET | `/api/v1/anomalies` | Active anomalies |
| GET | `/api/v1/gpu/utilisation` | Real-time GPU metrics |
| GET | `/api/v1/recommendations` | Ranked savings opportunities |
| POST | `/api/v1/llm/chat` | Unified LLM gateway |
| POST | `/api/v1/agent/chat` | FinOps AI assistant |
| WS | `/ws/costs/live` | Real-time cost stream |
| WS | `/ws/anomalies` | Live anomaly feed |

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `./scripts/test-all.sh`
4. Submit a PR

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built with ❤️ for FinOps teams managing AI workloads at scale across hybrid clouds.*
