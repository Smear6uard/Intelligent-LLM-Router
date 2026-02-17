from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class TaskType(str, Enum):
    CODE = "code"
    CREATIVE = "creative"
    MATH = "math"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    QA = "qa"
    MULTI_STEP = "multi_step"


class ModelName(str, Enum):
    CLAUDE_3_5_SONNET = "claude-3.5-sonnet"
    GPT_4O = "gpt-4o"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    DEEPSEEK_V3 = "deepseek-v3"
    GPT_4O_MINI = "gpt-4o-mini"
    CLAUDE_3_HAIKU = "claude-3-haiku"


class ComplexityBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --- Request Models ---

class ClassifyRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)


class CompletionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    stream: bool = True
    model: Optional[ModelName] = None  # Override routing


class ABTestRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    models: Optional[list[ModelName]] = None  # Auto-select if None


class VoteRequest(BaseModel):
    winner_model: ModelName


# --- Response Models ---

class ClassificationResult(BaseModel):
    task_type: TaskType
    complexity: float = Field(..., ge=1.0, le=10.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    signals: dict[str, float]
    recommended_model: ModelName
    routing_reason: str


class CompletionMetadata(BaseModel):
    request_id: str
    task_type: TaskType
    complexity: float
    confidence: float
    model: ModelName
    routing_reason: str
    was_routed: bool


class CompletionResponse(BaseModel):
    metadata: CompletionMetadata
    response_text: str
    latency_ms: int
    tokens_used: int
    cost_cents: float


class AnalyticsSummary(BaseModel):
    total_requests: int
    total_cost_cents: float
    avg_latency_ms: float
    avg_complexity: float
    hypothetical_cost_cents: float
    cost_savings_percent: float
    models_used: int
    requests_today: int
