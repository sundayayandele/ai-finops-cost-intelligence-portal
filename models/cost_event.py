"""
Unified Cost Event schema — single Pydantic model consumed by all microservices.
Both Azure and OpenStack ingestors produce this exact schema.
"""
from pydantic import BaseModel, Field
from enum import StrEnum
from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional, Literal


class CloudProvider(StrEnum):
    AZURE     = "azure"
    OPENSTACK = "openstack"


class WorkloadType(StrEnum):
    LLM_INFERENCE = "llm_inference"
    AGENT_SESSION = "agent_session"
    ML_TRAINING   = "ml_training"
    ML_INFERENCE  = "ml_inference"
    EMBEDDING     = "embedding"
    FINE_TUNING   = "fine_tuning"
    GPU_COMPUTE   = "gpu_compute"
    COGNITIVE_API = "cognitive_api"
    STORAGE       = "storage"


class UnifiedCostEvent(BaseModel):
    # ── Identity ───────────────────────────────────────────────
    event_id:      UUID         = Field(default_factory=uuid4)
    cloud:         CloudProvider
    workload_type: WorkloadType
    timestamp:     datetime     = Field(default_factory=datetime.utcnow)

    # ── Attribution (required for chargeback) ──────────────────
    tenant_id:     str          # Azure subscription ID / OpenStack project UUID
    region:        str          # "eastus" / "RegionOne"
    team:          str
    feature:       str
    env:           Literal["prod", "staging", "dev"]
    cost_centre:   str

    # ── Resource ────────────────────────────────────────────────
    resource_id:   str          # ARM resource ID / OpenStack instance UUID
    resource_type: str          # "azure-openai" / "vllm-endpoint" / "nova-gpu"
    model_name:    Optional[str] = None
    model_version: Optional[str] = None

    # ── Token Metrics (LLM workloads) ───────────────────────────
    prompt_tokens:     int = 0
    completion_tokens: int = 0
    cached_tokens:     int = 0   # semantic cache hits — excluded from cost
    total_tokens:      int = 0

    # ── Compute Metrics (GPU / ML workloads) ────────────────────
    gpu_hours:    float        = 0.0
    cpu_hours:    float        = 0.0
    gpu_type:     Optional[str] = None   # "A100" / "V100" / "T4" / "H100"
    gpu_util_pct: Optional[float] = None

    # ── Cost ────────────────────────────────────────────────────
    cost_usd:      float        # Normalised USD — Azure market rate OR OpenStack CapEx
    unit_rate_usd: float = 0.0  # Per-token or per-GPU-hour rate
    billing_model: Literal["payg", "reserved", "spot", "internal"]
    # "internal" = OpenStack showback / chargeback using CapEx amortised rates

    # ── Agentic AI ──────────────────────────────────────────────
    agent_session_id: Optional[str] = None
    tool_calls:       int = 0        # >50 triggers loop explosion alert
    context_tokens:   int = 0        # >80K triggers context bloat alert

    def effective_tokens(self) -> int:
        """Tokens actually billed (excluding cache hits)."""
        return max(0, self.prompt_tokens + self.completion_tokens - self.cached_tokens)

    class Config:
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat()}
