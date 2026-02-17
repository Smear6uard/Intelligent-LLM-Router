import asyncio
import random
import time
from models import ModelName, TaskType

# Latency ranges in ms per model
LATENCY_RANGES: dict[ModelName, tuple[int, int]] = {
    ModelName.GEMINI_1_5_PRO: (200, 800),
    ModelName.CLAUDE_3_HAIKU: (200, 600),
    ModelName.GPT_4O_MINI: (300, 700),
    ModelName.DEEPSEEK_V3: (300, 600),
    ModelName.CLAUDE_3_5_SONNET: (800, 3000),
    ModelName.GPT_4O: (600, 2500),
}

FAILURE_RATE = 0.05  # 5% simulated failure chance

# Mock response templates per task type
MOCK_RESPONSES: dict[TaskType, list[str]] = {
    TaskType.CODE: [
        "Here's a clean implementation for your request:\n\n```python\ndef solution(data):\n    # Validate input\n    if not data:\n        return []\n    \n    # Process using efficient algorithm\n    result = []\n    seen = set()\n    for item in data:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    \n    return result\n```\n\nThis solution runs in O(n) time complexity with O(n) space. The set-based lookup ensures we handle duplicates efficiently. You could also consider using `dict.fromkeys(data)` for a more Pythonic one-liner, though the explicit approach above is clearer for complex filtering logic.",
        "I'll break down the implementation step by step:\n\n```javascript\nasync function fetchWithRetry(url, options = {}, maxRetries = 3) {\n  for (let attempt = 0; attempt < maxRetries; attempt++) {\n    try {\n      const response = await fetch(url, options);\n      if (!response.ok) throw new Error(`HTTP ${response.status}`);\n      return await response.json();\n    } catch (error) {\n      if (attempt === maxRetries - 1) throw error;\n      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)));\n    }\n  }\n}\n```\n\nKey design decisions: exponential backoff prevents thundering herd issues, and we only retry on actual failures rather than business logic errors.",
    ],
    TaskType.CREATIVE: [
        "The morning light filtered through the old library's stained glass windows, casting kaleidoscope patterns across the worn oak floors. Eleanor traced her fingers along the spines of forgotten books, each one a doorway to a world that existed only in the space between reader and page.\n\n\"Every story is a conversation,\" her grandmother used to say. \"The author speaks, and the reader answers with their imagination.\"\n\nShe pulled a leather-bound volume from the shelf. Its pages smelled of vanilla and time — that particular sweetness of decomposing lignin that book lovers know instinctively. The title had faded to ghost letters, barely visible in the amber light.\n\nThis was the story she had been searching for.",
        "In the garden of forgotten algorithms, where binary trees bloom with recursive elegance and hash maps spread their roots through fertile memory, there lived a small function named Lambda.\n\nLambda was not like the other functions. While they boasted of their long parameter lists and complex return types, Lambda carried only what was needed — a single expression, pure and purposeful.\n\n\"Why do you travel so light?\" asked the heavyweight Constructor.\n\nLambda smiled. \"Because the best solutions are the ones that carry no more weight than the problem requires.\"",
    ],
    TaskType.MATH: [
        "Let me solve this step by step.\n\nGiven the equation, we first identify the key variables and relationships:\n\n**Step 1: Set up the equation**\nWe can express this as: f(x) = ax² + bx + c\n\n**Step 2: Apply the quadratic formula**\nx = (-b ± √(b² - 4ac)) / 2a\n\n**Step 3: Calculate the discriminant**\nΔ = b² - 4ac\n\nSince Δ > 0, we have two distinct real solutions.\n\n**Step 4: Compute the roots**\nx₁ = (-b + √Δ) / 2a\nx₂ = (-b - √Δ) / 2a\n\n**Result:** The solution set is {x₁, x₂}, which can be verified by substituting back into the original equation. The sum of roots equals -b/a and the product equals c/a, consistent with Vieta's formulas.",
        "To approach this problem, we'll use a combination of algebraic manipulation and calculus.\n\n**Given:** We need to find the optimal value.\n\n**Approach:** Taking the derivative and setting it to zero:\n\nf'(x) = 3x² - 12x + 9 = 0\n3(x² - 4x + 3) = 0\n3(x - 1)(x - 3) = 0\n\nCritical points: x = 1 and x = 3\n\n**Second derivative test:**\nf''(x) = 6x - 12\nf''(1) = -6 < 0 → local maximum at x = 1\nf''(3) = 6 > 0 → local minimum at x = 3\n\nThe maximum value is f(1) = 1 - 6 + 9 + 2 = 6.",
    ],
    TaskType.SUMMARIZATION: [
        "Here are the key points:\n\n• **Main Thesis**: The central argument revolves around the intersection of technology and human behavior, emphasizing how digital tools reshape cognitive patterns rather than simply augmenting existing ones.\n\n• **Key Findings**: Research indicates a measurable shift in attention spans and information processing, though the effect is more nuanced than popular narratives suggest.\n\n• **Implications**: Organizations should design systems that leverage these changes rather than resist them, focusing on information architecture that matches modern cognitive patterns.\n\n• **Conclusion**: The relationship between technology and cognition is bidirectional — we shape our tools, and they shape us in return.",
        "**Summary:**\n\nThe document outlines three primary recommendations:\n\n1. **Restructure the workflow** to prioritize asynchronous communication, reducing meeting overhead by an estimated 30%.\n\n2. **Implement automated quality checks** at each pipeline stage, catching defects earlier in the process where they cost 10x less to fix.\n\n3. **Adopt incremental delivery** over big-bang releases, allowing faster feedback loops and reducing deployment risk.\n\nThe projected impact is a 25% improvement in throughput with 15% cost reduction over 6 months.",
    ],
    TaskType.TRANSLATION: [
        "Here is the translation:\n\nThe text has been carefully translated while preserving the original tone and nuance. I've maintained the formal register of the source material and adapted idiomatic expressions to sound natural in the target language.\n\nKey translation choices:\n- Cultural references have been localized where appropriate\n- Technical terminology follows standard conventions in the target language\n- Sentence structure has been adjusted to follow natural word order patterns\n\nNote: Some phrases required interpretation rather than literal translation to convey the intended meaning accurately.",
        "Translation complete. Here is the result with annotations:\n\nThe passage has been translated with attention to both accuracy and readability. A few notes on specific choices:\n\n1. **Formal/informal register**: Maintained the formal tone of the original\n2. **Idiomatic expressions**: Adapted to equivalent expressions in the target language rather than translating literally\n3. **Proper nouns**: Kept in their original form as per standard practice\n4. **Technical terms**: Used the widely accepted translations in the field\n\nThe translation aims to read naturally while staying faithful to the source material's meaning and intent.",
    ],
    TaskType.QA: [
        "Great question! Here's a clear explanation:\n\nThe concept works by establishing a relationship between input and output through a well-defined set of rules. Think of it like a recipe — you have ingredients (inputs), a process (the algorithm), and a result (output).\n\n**Key points:**\n- It operates on the principle of determinism: same input always produces same output\n- The efficiency depends on the data structure chosen for the underlying storage\n- Common use cases include search optimization, data validation, and pattern matching\n\nIn practice, you'll encounter this most often when dealing with data processing pipelines or API design. The important thing to remember is that the choice of approach should be driven by your specific constraints — there's rarely a one-size-fits-all solution.",
        "The answer depends on context, but here's the general explanation:\n\nAt its core, this works through a layered architecture where each layer has a specific responsibility. The bottom layer handles raw data, the middle layer manages business logic, and the top layer handles presentation.\n\n**Why it matters:**\n1. Separation of concerns makes the system easier to maintain\n2. Each layer can be tested independently\n3. Changes in one layer don't cascade through the entire system\n\n**Common misconception:** Many people think this adds unnecessary complexity, but for any system beyond trivial size, the organizational benefits far outweigh the initial setup cost.\n\nWould you like me to elaborate on any specific aspect?",
    ],
    TaskType.MULTI_STEP: [
        "Here's a comprehensive step-by-step guide:\n\n## Phase 1: Setup & Configuration\n1. Initialize the project structure with the required dependencies\n2. Configure the environment variables and connection settings\n3. Set up the development and staging environments\n\n## Phase 2: Core Implementation\n4. Build the data models and validation layer\n5. Implement the core business logic\n6. Create the API endpoints with proper error handling\n7. Add authentication and authorization middleware\n\n## Phase 3: Testing & Deployment\n8. Write unit tests for critical paths\n9. Perform integration testing with realistic data\n10. Set up CI/CD pipeline for automated deployment\n11. Deploy to staging, verify, then promote to production\n\n**Estimated timeline:** Each phase builds on the previous one. Phase 1 is the foundation — don't skip any steps here as issues compound later.\n\n**Pro tip:** Keep a checklist and verify each step before moving to the next. It's much easier to fix issues in the current phase than to debug them three phases later.",
        "Let me break this down into manageable steps:\n\n### Step 1: Analysis\nFirst, we need to understand the current state. Audit the existing system, identify bottlenecks, and document the key pain points.\n\n### Step 2: Design\nCreate a solution architecture that addresses each identified issue. Consider:\n- Scalability requirements\n- Integration points with existing systems\n- Data migration strategy\n\n### Step 3: Implementation\nBuild iteratively, starting with the highest-impact, lowest-risk changes:\n- Core functionality first\n- Edge cases and error handling second\n- Performance optimization third\n\n### Step 4: Validation\nTest each component individually, then as an integrated system. Use realistic data volumes and access patterns.\n\n### Step 5: Rollout\nDeploy gradually using a phased approach. Monitor key metrics at each stage and have a rollback plan ready.\n\nEach step has clear entry and exit criteria. Do not proceed to the next step until the current one meets its acceptance criteria.",
    ],
}


def _simulate_latency(model: ModelName) -> int:
    """Get simulated latency in milliseconds."""
    low, high = LATENCY_RANGES[model]
    return random.randint(low, high)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~0.75 tokens per word."""
    return max(10, int(len(text.split()) * 0.75))


def _should_fail() -> bool:
    """Simulate random failure (5% chance)."""
    return random.random() < FAILURE_RATE


def get_mock_response(task_type: TaskType, model: ModelName) -> str:
    """Get a mock response for the given task type."""
    templates = MOCK_RESPONSES.get(task_type, MOCK_RESPONSES[TaskType.QA])
    response = random.choice(templates)
    # Add model-specific flavor
    model_prefix = {
        ModelName.CLAUDE_3_5_SONNET: "",
        ModelName.GPT_4O: "",
        ModelName.GEMINI_1_5_PRO: "",
        ModelName.DEEPSEEK_V3: "",
        ModelName.GPT_4O_MINI: "",
        ModelName.CLAUDE_3_HAIKU: "",
    }
    return model_prefix.get(model, "") + response


async def generate_completion(
    task_type: TaskType,
    model: ModelName,
) -> dict:
    """Generate a mock completion with simulated latency. Returns full response."""
    if _should_fail():
        raise RuntimeError(f"Simulated failure for model {model.value}")

    latency_ms = _simulate_latency(model)
    await asyncio.sleep(latency_ms / 1000.0)

    response_text = get_mock_response(task_type, model)
    tokens = _estimate_tokens(response_text)

    return {
        "response_text": response_text,
        "latency_ms": latency_ms,
        "tokens_used": tokens,
    }


async def stream_completion(
    task_type: TaskType,
    model: ModelName,
):
    """Async generator that yields word-by-word chunks with delays."""
    if _should_fail():
        raise RuntimeError(f"Simulated failure for model {model.value}")

    start = time.time()
    response_text = get_mock_response(task_type, model)
    words = response_text.split(" ")
    tokens = _estimate_tokens(response_text)

    # Simulate initial model thinking time
    base_delay = LATENCY_RANGES[model][0] / 1000.0
    await asyncio.sleep(base_delay * random.uniform(0.5, 1.0))

    yielded_text = []
    for i, word in enumerate(words):
        chunk = word if i == 0 else " " + word
        yielded_text.append(chunk)
        yield {"type": "chunk", "content": chunk}
        # Variable inter-chunk delay: 10-50ms
        await asyncio.sleep(random.uniform(0.01, 0.05))

    elapsed_ms = int((time.time() - start) * 1000)

    yield {
        "type": "done",
        "response_text": response_text,
        "latency_ms": elapsed_ms,
        "tokens_used": tokens,
    }
