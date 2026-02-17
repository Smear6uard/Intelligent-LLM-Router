import re
from models import TaskType


# --- Task Type Detection ---

TASK_PATTERNS: dict[TaskType, dict] = {
    TaskType.CODE: {
        "keywords": [
            "function", "code", "program", "implement", "debug", "refactor",
            "algorithm", "api", "class", "method", "variable", "loop",
            "syntax", "compile", "runtime", "database", "query", "sql",
            "python", "javascript", "typescript", "java", "rust", "golang",
            "html", "css", "react", "django", "flask", "fastapi",
        ],
        "patterns": [
            r"write\s+(?:a\s+)?(?:python|javascript|java|c\+\+|rust|go|typescript)",
            r"(?:fix|debug|refactor)\s+(?:this|the|my)\s+code",
            r"implement\s+(?:a\s+)?(?:function|class|method|api|endpoint)",
            r"```[\s\S]*```",
            r"how\s+(?:do|can|to)\s+(?:i\s+)?(?:code|program|implement)",
        ],
        "weight": 1.0,
    },
    TaskType.CREATIVE: {
        "keywords": [
            "write", "story", "poem", "essay", "creative", "fiction",
            "character", "narrative", "dialogue", "metaphor", "imagine",
            "compose", "draft", "blog", "article", "screenplay", "lyric",
        ],
        "patterns": [
            r"write\s+(?:a\s+)?(?:story|poem|essay|article|blog|screenplay)",
            r"(?:creative|fiction|narrative)\s+writing",
            r"imagine\s+(?:a|that|if)",
            r"compose\s+(?:a\s+)?(?:poem|letter|song|email)",
        ],
        "weight": 1.0,
    },
    TaskType.MATH: {
        "keywords": [
            "calculate", "solve", "equation", "math", "algebra", "calculus",
            "probability", "statistics", "integral", "derivative", "proof",
            "theorem", "formula", "geometric", "trigonometry", "matrix",
            "vector", "optimization", "linear", "quadratic",
        ],
        "patterns": [
            r"(?:solve|calculate|compute|evaluate|find)\s+(?:the|this|for)",
            r"\d+\s*[\+\-\*\/\^]\s*\d+",
            r"(?:integral|derivative|limit)\s+of",
            r"(?:prove|show)\s+that",
            r"what\s+is\s+\d+",
        ],
        "weight": 1.0,
    },
    TaskType.SUMMARIZATION: {
        "keywords": [
            "summarize", "summary", "tldr", "brief", "condense", "overview",
            "key points", "main ideas", "recap", "digest", "abstract",
            "shorten", "highlights",
        ],
        "patterns": [
            r"(?:summarize|sum up|give\s+(?:a|me)\s+(?:a\s+)?summary)",
            r"(?:tldr|tl;dr|too\s+long)",
            r"(?:key|main|important)\s+(?:points|ideas|takeaways)",
            r"(?:brief|short|concise)\s+(?:overview|summary|description)",
        ],
        "weight": 1.0,
    },
    TaskType.TRANSLATION: {
        "keywords": [
            "translate", "translation", "convert", "language", "spanish",
            "french", "german", "chinese", "japanese", "korean", "arabic",
            "portuguese", "italian", "russian", "hindi", "localize",
        ],
        "patterns": [
            r"translate\s+(?:this|the|following|into|to|from)",
            r"(?:from|into|to)\s+(?:english|spanish|french|german|chinese|japanese|korean|arabic|portuguese|italian|russian|hindi)",
            r"(?:in|to)\s+\w+\s+(?:language|translation)",
            r"how\s+(?:do\s+you\s+)?say\s+.+\s+in\s+\w+",
        ],
        "weight": 1.0,
    },
    TaskType.QA: {
        "keywords": [
            "what", "who", "where", "when", "why", "how", "explain",
            "define", "describe", "tell", "meaning", "difference",
            "compare", "example", "does", "is", "are", "can",
        ],
        "patterns": [
            r"^(?:what|who|where|when|why|how)\s+",
            r"(?:explain|describe|define)\s+(?:the|what|how)",
            r"what\s+(?:is|are|does|do)\s+",
            r"(?:can|could)\s+you\s+(?:explain|tell|describe)",
            r"(?:difference|comparison)\s+between",
        ],
        "weight": 0.8,  # Lower weight since QA keywords are common
    },
    TaskType.MULTI_STEP: {
        "keywords": [
            "step", "steps", "first", "then", "next", "finally",
            "process", "workflow", "pipeline", "plan", "strategy",
            "guide", "tutorial", "walkthrough", "instructions", "procedure",
        ],
        "patterns": [
            r"step[\s-]by[\s-]step",
            r"(?:first|then|next|finally|after\s+that)",
            r"(?:create|build|design|develop)\s+(?:a\s+)?(?:complete|full|entire)",
            r"(?:how\s+to|guide\s+(?:to|for|on))\s+(?:build|create|set\s+up|deploy)",
            r"(?:plan|strategy|roadmap)\s+for",
        ],
        "weight": 1.0,
    },
}

# Reasoning depth markers
REASONING_WORDS = [
    "because", "therefore", "however", "although", "whereas",
    "if", "then", "else", "unless", "assuming",
    "compare", "contrast", "analyze", "evaluate", "assess",
    "pros and cons", "trade-off", "implications", "consequences",
    "on the other hand", "alternatively", "furthermore", "moreover",
    "considering", "given that", "in light of",
]

# Domain-specific vocabulary
DOMAIN_VOCAB = {
    "medical": ["diagnosis", "symptom", "treatment", "patient", "clinical", "pathology",
                 "pharmaceutical", "dosage", "prognosis", "etiology", "comorbidity"],
    "legal": ["jurisdiction", "statute", "liability", "plaintiff", "defendant",
              "precedent", "tort", "breach", "contractual", "indemnity", "arbitration"],
    "financial": ["portfolio", "derivative", "hedge", "amortization", "equity",
                  "dividend", "liquidity", "volatility", "arbitrage", "securities"],
    "scientific": ["hypothesis", "methodology", "empirical", "quantitative", "peer-reviewed",
                   "replication", "variance", "coefficient", "correlation", "longitudinal"],
}

# Inherent complexity per task type
TASK_BASE_COMPLEXITY = {
    TaskType.CODE: 6.0,
    TaskType.CREATIVE: 5.0,
    TaskType.MATH: 7.0,
    TaskType.SUMMARIZATION: 3.0,
    TaskType.TRANSLATION: 4.0,
    TaskType.QA: 3.0,
    TaskType.MULTI_STEP: 7.0,
}


def detect_task_type(prompt: str) -> tuple[TaskType, float]:
    """Detect the task type from prompt text. Returns (task_type, confidence)."""
    prompt_lower = prompt.lower()
    scores: dict[TaskType, float] = {}

    for task_type, config in TASK_PATTERNS.items():
        keyword_hits = sum(1 for kw in config["keywords"] if kw in prompt_lower)
        regex_hits = sum(1 for pat in config["patterns"] if re.search(pat, prompt_lower))
        scores[task_type] = (keyword_hits * 1.0 + regex_hits * 2.0) * config["weight"]

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_type, top_score = sorted_scores[0]
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

    confidence = top_score / (top_score + second_score + 0.001) if top_score > 0 else 0.3

    # Default to QA if no strong signal
    if top_score == 0:
        return TaskType.QA, 0.3

    return top_type, round(min(1.0, confidence), 3)


def compute_complexity(prompt: str, task_type: TaskType, confidence: float) -> tuple[float, dict[str, float]]:
    """Compute complexity score (1.0-10.0) from multiple signals."""
    words = prompt.split()
    word_count = len(words)
    prompt_lower = prompt.lower()

    # Signal 1: Token length
    token_length = min(10.0, word_count / 50.0 * 10.0)

    # Signal 2: Task type base complexity, scaled by confidence
    task_base = TASK_BASE_COMPLEXITY.get(task_type, 5.0)
    task_type_match = task_base * confidence

    # Signal 3: Reasoning depth
    reasoning_hits = sum(1 for w in REASONING_WORDS if w in prompt_lower)
    reasoning_depth = min(10.0, reasoning_hits * 1.5)

    # Signal 4: Domain specificity
    domain_hits = 0
    for terms in DOMAIN_VOCAB.values():
        domain_hits += sum(1 for t in terms if t in prompt_lower)
    domain_specificity = min(10.0, domain_hits * 2.5)

    # Signal 5: Context needs
    context_score = 0.0
    context_refs = ["above", "previous", "earlier", "mentioned", "as shown", "given the"]
    context_score += sum(2.0 for ref in context_refs if ref in prompt_lower)
    if prompt.count("\n") > 3:
        context_score += 2.0
    if word_count > 200:
        context_score += 3.0
    context_needs = min(10.0, context_score)

    # Signal 6: Vocabulary complexity (avg word length as proxy)
    avg_word_len = sum(len(w) for w in words) / max(1, word_count)
    vocabulary_complexity = min(10.0, (avg_word_len - 3.0) * 2.5)
    vocabulary_complexity = max(0.0, vocabulary_complexity)

    signals = {
        "token_length": round(token_length, 2),
        "task_type_match": round(task_type_match, 2),
        "reasoning_depth": round(reasoning_depth, 2),
        "domain_specificity": round(domain_specificity, 2),
        "context_needs": round(context_needs, 2),
        "vocabulary_complexity": round(vocabulary_complexity, 2),
    }

    # Weighted average
    weights = {
        "token_length": 0.20,
        "task_type_match": 0.15,
        "reasoning_depth": 0.25,
        "domain_specificity": 0.15,
        "context_needs": 0.15,
        "vocabulary_complexity": 0.10,
    }

    raw = sum(signals[k] * weights[k] for k in weights)
    complexity = max(1.0, min(10.0, round(raw, 1)))

    return complexity, signals


def classify(prompt: str) -> dict:
    """Full classification pipeline: task type + complexity + signals."""
    task_type, confidence = detect_task_type(prompt)
    complexity, signals = compute_complexity(prompt, task_type, confidence)

    return {
        "task_type": task_type,
        "complexity": complexity,
        "confidence": confidence,
        "signals": signals,
    }
