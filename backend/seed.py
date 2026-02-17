import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta

from models import TaskType, ModelName
from classifier import classify
from router import select_model, calculate_cost, complexity_to_band, ROUTING_MATRIX
from database import get_db

# Prompt templates per task type with variable slots
PROMPT_TEMPLATES: dict[TaskType, list[str]] = {
    TaskType.CODE: [
        "Write a Python function to {action}",
        "Implement a {language} class for {concept}",
        "Debug this {language} code that {problem}",
        "Refactor the following {language} code for better performance",
        "Create an API endpoint in {framework} that {action}",
        "Write unit tests for a {concept} module in {language}",
        "Implement a {data_structure} in {language} with {operation} support",
        "How do I implement {pattern} pattern in {language}?",
    ],
    TaskType.CREATIVE: [
        "Write a short story about {topic}",
        "Compose a poem about {topic} in the style of {style}",
        "Write a blog post about {topic}",
        "Create a fictional dialogue between {character1} and {character2}",
        "Write a product description for {product}",
        "Compose an email announcing {event}",
    ],
    TaskType.MATH: [
        "Solve the equation: {equation}",
        "Calculate the {operation} of {expression}",
        "Prove that {theorem}",
        "Find the optimal solution for {problem}",
        "What is the probability of {event}?",
        "Compute the {transform} of f(x) = {function}",
    ],
    TaskType.SUMMARIZATION: [
        "Summarize the key points of {topic}",
        "Give me a TLDR of {document_type} about {topic}",
        "What are the main takeaways from {topic}?",
        "Condense this {document_type} into bullet points",
        "Provide a brief overview of {topic}",
    ],
    TaskType.TRANSLATION: [
        "Translate the following text to {language}: {text}",
        "How do you say '{phrase}' in {language}?",
        "Translate this {document_type} from {source_lang} to {target_lang}",
        "Convert this technical documentation to {language}",
    ],
    TaskType.QA: [
        "What is {concept}?",
        "Explain the difference between {concept1} and {concept2}",
        "How does {technology} work?",
        "What are the pros and cons of {approach}?",
        "Why is {concept} important in {field}?",
        "Can you explain {concept} in simple terms?",
        "What is the best practice for {topic}?",
    ],
    TaskType.MULTI_STEP: [
        "Create a step-by-step guide to {action}",
        "Walk me through the process of {process}",
        "How do I set up a complete {system} from scratch?",
        "Design a workflow for {process}",
        "Build a complete {project} with {requirements}",
    ],
}

# Variable slot fillers
SLOT_FILLERS = {
    "action": ["sort a list", "parse JSON", "handle file uploads", "implement pagination",
               "validate emails", "build a REST API", "create a websocket server", "manage state"],
    "language": ["Python", "JavaScript", "TypeScript", "Java", "Rust", "Go"],
    "concept": ["binary search tree", "LRU cache", "graph traversal", "observer pattern",
                "microservices", "event-driven architecture", "dependency injection",
                "machine learning", "neural networks", "blockchain"],
    "problem": ["throws a TypeError", "has a memory leak", "runs too slowly",
                "produces incorrect output", "fails on edge cases"],
    "framework": ["FastAPI", "Express.js", "Django", "Flask", "Spring Boot"],
    "data_structure": ["hash map", "priority queue", "trie", "red-black tree", "skip list"],
    "operation": ["insert, delete, and search", "push and pop", "enqueue and dequeue"],
    "pattern": ["singleton", "factory", "observer", "strategy", "decorator"],
    "topic": ["artificial intelligence", "climate change", "remote work", "space exploration",
              "quantum computing", "sustainable energy", "cybersecurity", "digital privacy",
              "machine learning ethics", "the future of education"],
    "style": ["Shakespeare", "Emily Dickinson", "haiku", "free verse", "limerick"],
    "character1": ["a scientist", "a philosopher", "an AI", "a time traveler"],
    "character2": ["an artist", "a historian", "a child", "an alien"],
    "product": ["a smart home device", "an eco-friendly water bottle", "a productivity app"],
    "event": ["a product launch", "a team milestone", "a company retreat"],
    "equation": ["3x² - 12x + 9 = 0", "∫(x² + 2x)dx from 0 to 5", "lim(x→0) sin(x)/x"],
    "expression": ["the series 1 + 1/2 + 1/4 + ...", "matrix A × B", "5! / (3! × 2!)"],
    "theorem": ["the sum of angles in a triangle is 180°", "√2 is irrational",
                "there are infinitely many primes"],
    "transform": ["Fourier transform", "Laplace transform", "derivative"],
    "function": ["x² + 3x - 7", "e^(-x²)", "sin(x)/x", "ln(x² + 1)"],
    "document_type": ["research paper", "article", "report", "whitepaper", "blog post"],
    "phrase": ["Good morning", "Thank you very much", "Where is the library?",
              "I would like to order", "How much does this cost?"],
    "source_lang": ["English", "Spanish", "French", "German"],
    "target_lang": ["Spanish", "French", "Japanese", "Chinese", "Korean", "Portuguese"],
    "technology": ["Docker", "Kubernetes", "GraphQL", "WebAssembly", "gRPC"],
    "concept1": ["REST", "SQL", "monolith", "TCP", "encryption"],
    "concept2": ["GraphQL", "NoSQL", "microservices", "UDP", "hashing"],
    "approach": ["serverless architecture", "monorepo", "test-driven development",
                "pair programming", "agile methodology"],
    "field": ["software engineering", "data science", "cybersecurity", "DevOps"],
    "process": ["deploying to production", "setting up CI/CD", "migrating a database",
               "conducting a code review", "onboarding a new developer"],
    "system": ["monitoring stack", "authentication system", "data pipeline",
              "containerized development environment"],
    "project": ["full-stack web app", "CLI tool", "REST API", "mobile app backend"],
    "requirements": ["authentication, CRUD operations, and real-time updates",
                    "caching, rate limiting, and logging",
                    "testing, documentation, and deployment"],
}


def _fill_template(template: str) -> str:
    """Fill template slots with random values."""
    import re
    def replacer(match):
        key = match.group(1)
        if key in SLOT_FILLERS:
            return random.choice(SLOT_FILLERS[key])
        return match.group(0)
    return re.sub(r"\{(\w+)\}", replacer, template)


def _generate_prompt(task_type: TaskType) -> str:
    """Generate a realistic prompt for the given task type."""
    templates = PROMPT_TEMPLATES[task_type]
    template = random.choice(templates)
    return _fill_template(template)


def _random_timestamp(days_back: int = 7) -> str:
    """Generate a random timestamp within the past N days, business-hour weighted."""
    now = datetime.utcnow()
    day_offset = random.random() ** 0.7 * days_back  # Bias toward recent
    base = now - timedelta(days=day_offset)

    # Business hour weighting (9am-6pm more likely)
    hour = random.choices(
        range(24),
        weights=[1, 1, 1, 1, 1, 1, 2, 3, 5, 8, 8, 7, 6, 7, 8, 8, 7, 5, 3, 2, 2, 1, 1, 1],
    )[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    ts = base.replace(hour=hour, minute=minute, second=second, microsecond=0)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


async def seed_database():
    """Generate and insert seed data: 223 requests + 18 A/B tests."""
    db = await get_db()

    # Check if already seeded
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM requests")
    row = await cursor.fetchone()
    if row[0] > 0:
        return row[0]

    # Task type distribution
    type_weights = {
        TaskType.CODE: 0.19,
        TaskType.QA: 0.18,
        TaskType.CREATIVE: 0.14,
        TaskType.SUMMARIZATION: 0.13,
        TaskType.MATH: 0.12,
        TaskType.MULTI_STEP: 0.10,
        TaskType.TRANSLATION: 0.10,
    }
    # Force approximately 4% remaining to round out
    remaining = 1.0 - sum(type_weights.values())
    type_weights[TaskType.QA] += remaining

    total_requests = 223
    requests_data = []

    # Target: ~50% low, ~30% medium, ~20% high complexity
    # This creates the ~40% cost savings narrative
    complexity_distribution = (
        [random.uniform(1.0, 3.0) for _ in range(int(total_requests * 0.50))] +
        [random.uniform(3.5, 6.0) for _ in range(int(total_requests * 0.30))] +
        [random.uniform(6.5, 10.0) for _ in range(total_requests - int(total_requests * 0.50) - int(total_requests * 0.30))]
    )
    random.shuffle(complexity_distribution)

    from gateway import LATENCY_RANGES

    for i in range(total_requests):
        task_type = random.choices(
            list(type_weights.keys()),
            weights=list(type_weights.values()),
        )[0]

        prompt = _generate_prompt(task_type)
        complexity = round(complexity_distribution[i], 1)
        confidence = round(random.uniform(0.55, 0.95), 3)

        model, reason = select_model(task_type, complexity)

        # Simulate tokens (higher complexity → more tokens)
        base_tokens = int(50 + complexity * 70)
        tokens = random.randint(base_tokens, base_tokens + 200)
        lat_range = LATENCY_RANGES[model]
        latency_ms = random.randint(lat_range[0], lat_range[1])
        cost = calculate_cost(model, tokens)

        requests_data.append({
            "id": str(uuid.uuid4()),
            "prompt": prompt,
            "task_type": task_type.value,
            "complexity": complexity,
            "confidence": confidence,
            "model": model.value,
            "was_routed": 1,
            "response_text": f"[Seeded response for {task_type.value}]",
            "latency_ms": latency_ms,
            "tokens_used": tokens,
            "cost_cents": cost,
            "created_at": _random_timestamp(7),
        })

    # Bulk insert requests
    await db.executemany(
        """INSERT INTO requests (id, prompt, task_type, complexity, confidence,
           model, was_routed, response_text, latency_ms, tokens_used, cost_cents, created_at)
           VALUES (:id, :prompt, :task_type, :complexity, :confidence,
           :model, :was_routed, :response_text, :latency_ms, :tokens_used, :cost_cents, :created_at)""",
        requests_data,
    )

    # Seed A/B tests
    ab_tests = []
    ab_results = []
    all_models = list(ModelName)

    for _ in range(18):
        task_type = random.choice(list(TaskType))
        prompt = _generate_prompt(task_type)
        classification = classify(prompt)
        complexity = classification["complexity"]

        test_models = random.sample(all_models, k=random.choice([2, 3]))
        test_id = str(uuid.uuid4())

        # Randomly assign a winner (or None for ~30% of tests)
        winner = random.choice(test_models).value if random.random() > 0.3 else None

        ab_tests.append({
            "id": test_id,
            "prompt": prompt,
            "task_type": task_type.value,
            "complexity": complexity,
            "models": json.dumps([m.value for m in test_models]),
            "winner_model": winner,
            "created_at": _random_timestamp(7),
        })

        for model in test_models:
            tokens = random.randint(80, 600)
            lat_range = LATENCY_RANGES[model]
            latency_ms = random.randint(lat_range[0], lat_range[1])
            cost = calculate_cost(model, tokens)

            ab_results.append({
                "id": str(uuid.uuid4()),
                "ab_test_id": test_id,
                "model": model.value,
                "response_text": f"[Seeded A/B response for {model.value}]",
                "latency_ms": latency_ms,
                "tokens_used": tokens,
                "cost_cents": cost,
            })

    await db.executemany(
        """INSERT INTO ab_tests (id, prompt, task_type, complexity, models, winner_model, created_at)
           VALUES (:id, :prompt, :task_type, :complexity, :models, :winner_model, :created_at)""",
        ab_tests,
    )

    await db.executemany(
        """INSERT INTO ab_results (id, ab_test_id, model, response_text, latency_ms, tokens_used, cost_cents)
           VALUES (:id, :ab_test_id, :model, :response_text, :latency_ms, :tokens_used, :cost_cents)""",
        ab_results,
    )

    await db.commit()
    return total_requests
