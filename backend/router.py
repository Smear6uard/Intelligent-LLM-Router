from models import TaskType, ModelName, ComplexityBand

# Cost per 1K tokens in cents
MODEL_COSTS: dict[ModelName, float] = {
    ModelName.CLAUDE_3_5_SONNET: 0.30,
    ModelName.GPT_4O: 0.25,
    ModelName.GEMINI_1_5_PRO: 0.18,
    ModelName.DEEPSEEK_V3: 0.14,
    ModelName.GPT_4O_MINI: 0.015,
    ModelName.CLAUDE_3_HAIKU: 0.008,
}

# Hypothetical "always use best model" cost for savings calculation
EXPENSIVE_MODEL_COST = MODEL_COSTS[ModelName.CLAUDE_3_5_SONNET]

# Routing matrix: (task_type, complexity_band) -> model
ROUTING_MATRIX: dict[TaskType, dict[ComplexityBand, ModelName]] = {
    TaskType.CODE: {
        ComplexityBand.LOW: ModelName.GPT_4O_MINI,
        ComplexityBand.MEDIUM: ModelName.CLAUDE_3_5_SONNET,
        ComplexityBand.HIGH: ModelName.CLAUDE_3_5_SONNET,
    },
    TaskType.MATH: {
        ComplexityBand.LOW: ModelName.GPT_4O_MINI,
        ComplexityBand.MEDIUM: ModelName.DEEPSEEK_V3,
        ComplexityBand.HIGH: ModelName.DEEPSEEK_V3,
    },
    TaskType.CREATIVE: {
        ComplexityBand.LOW: ModelName.GPT_4O_MINI,
        ComplexityBand.MEDIUM: ModelName.GPT_4O,
        ComplexityBand.HIGH: ModelName.CLAUDE_3_5_SONNET,
    },
    TaskType.SUMMARIZATION: {
        ComplexityBand.LOW: ModelName.CLAUDE_3_HAIKU,
        ComplexityBand.MEDIUM: ModelName.GPT_4O_MINI,
        ComplexityBand.HIGH: ModelName.GEMINI_1_5_PRO,
    },
    TaskType.QA: {
        ComplexityBand.LOW: ModelName.CLAUDE_3_HAIKU,
        ComplexityBand.MEDIUM: ModelName.GPT_4O_MINI,
        ComplexityBand.HIGH: ModelName.GPT_4O,
    },
    TaskType.TRANSLATION: {
        ComplexityBand.LOW: ModelName.GPT_4O_MINI,
        ComplexityBand.MEDIUM: ModelName.GPT_4O,
        ComplexityBand.HIGH: ModelName.GPT_4O,
    },
    TaskType.MULTI_STEP: {
        ComplexityBand.LOW: ModelName.GPT_4O_MINI,
        ComplexityBand.MEDIUM: ModelName.CLAUDE_3_5_SONNET,
        ComplexityBand.HIGH: ModelName.CLAUDE_3_5_SONNET,
    },
}

# Reasons for routing decisions
ROUTING_REASONS = {
    ModelName.CLAUDE_3_5_SONNET: "Best for complex reasoning and code generation",
    ModelName.GPT_4O: "Strong general-purpose model for medium-high complexity",
    ModelName.GEMINI_1_5_PRO: "Excellent for long-context summarization tasks",
    ModelName.DEEPSEEK_V3: "Specialized in mathematical and logical reasoning",
    ModelName.GPT_4O_MINI: "Cost-efficient for straightforward tasks",
    ModelName.CLAUDE_3_HAIKU: "Ultra-fast and cheap for simple lookups",
}

# Fallback order for retry logic
FALLBACK_ORDER: dict[ModelName, ModelName] = {
    ModelName.CLAUDE_3_5_SONNET: ModelName.GPT_4O,
    ModelName.GPT_4O: ModelName.CLAUDE_3_5_SONNET,
    ModelName.GEMINI_1_5_PRO: ModelName.GPT_4O,
    ModelName.DEEPSEEK_V3: ModelName.GPT_4O_MINI,
    ModelName.GPT_4O_MINI: ModelName.CLAUDE_3_HAIKU,
    ModelName.CLAUDE_3_HAIKU: ModelName.GPT_4O_MINI,
}


def complexity_to_band(complexity: float) -> ComplexityBand:
    if complexity <= 3.0:
        return ComplexityBand.LOW
    elif complexity <= 6.0:
        return ComplexityBand.MEDIUM
    else:
        return ComplexityBand.HIGH


def select_model(task_type: TaskType, complexity: float) -> tuple[ModelName, str]:
    """Select the optimal model based on task type and complexity."""
    band = complexity_to_band(complexity)
    model = ROUTING_MATRIX[task_type][band]
    reason = f"{ROUTING_REASONS[model]} (complexity {complexity:.1f}, band={band.value})"
    return model, reason


def calculate_cost(model: ModelName, tokens: int) -> float:
    """Calculate cost in cents for a given model and token count."""
    return round(MODEL_COSTS[model] * tokens / 1000, 4)


def calculate_hypothetical_cost(tokens: int) -> float:
    """What it would cost if we always used the most expensive model."""
    return round(EXPENSIVE_MODEL_COST * tokens / 1000, 4)
