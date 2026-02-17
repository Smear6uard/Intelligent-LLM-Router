import asyncio
import json
import uuid
from models import ModelName, TaskType
from gateway import generate_completion
from router import calculate_cost
from database import insert_ab_test, insert_ab_result, execute
import config
import gateway_live

# Default models to compare if user doesn't specify
DEFAULT_AB_MODELS: dict[TaskType, list[ModelName]] = {
    TaskType.CODE: [ModelName.CLAUDE_3_5_SONNET, ModelName.GPT_4O, ModelName.GPT_4O_MINI],
    TaskType.MATH: [ModelName.DEEPSEEK_V3, ModelName.GPT_4O, ModelName.GPT_4O_MINI],
    TaskType.CREATIVE: [ModelName.CLAUDE_3_5_SONNET, ModelName.GPT_4O, ModelName.GPT_4O_MINI],
    TaskType.SUMMARIZATION: [ModelName.GEMINI_1_5_PRO, ModelName.GPT_4O_MINI, ModelName.CLAUDE_3_HAIKU],
    TaskType.QA: [ModelName.GPT_4O, ModelName.GPT_4O_MINI, ModelName.CLAUDE_3_HAIKU],
    TaskType.TRANSLATION: [ModelName.GPT_4O, ModelName.GPT_4O_MINI, ModelName.CLAUDE_3_5_SONNET],
    TaskType.MULTI_STEP: [ModelName.CLAUDE_3_5_SONNET, ModelName.GPT_4O, ModelName.GPT_4O_MINI],
}


def get_ab_models(task_type: TaskType, requested: list[ModelName] | None) -> list[ModelName]:
    """Get models for A/B test. Use requested or default per task type."""
    if requested and len(requested) >= 2:
        return requested[:3]  # Max 3 models
    return DEFAULT_AB_MODELS.get(task_type, [ModelName.GPT_4O, ModelName.GPT_4O_MINI])


async def run_ab_test(
    prompt: str,
    task_type: TaskType,
    complexity: float,
    models: list[ModelName],
) -> dict:
    """Run prompt against multiple models in parallel and return results."""
    test_id = str(uuid.uuid4())

    # Save AB test record
    await insert_ab_test({
        "id": test_id,
        "prompt": prompt,
        "task_type": task_type.value,
        "complexity": complexity,
        "models": json.dumps([m.value for m in models]),
    })

    # Determine mode once for all models
    current_mode = config.get_mode()
    if current_mode == "live":
        under_cap = await config.check_spend_cap()
        if not under_cap:
            current_mode = "demo"

    # Run all models in parallel
    async def run_single(model: ModelName) -> dict:
        try:
            if current_mode == "live":
                api_key = config.get_api_key()
                result = await gateway_live.generate_completion_live(prompt, model, api_key)
            else:
                result = await generate_completion(task_type, model)

            cost = calculate_cost(model, result["tokens_used"])
            result_id = str(uuid.uuid4())

            await insert_ab_result({
                "id": result_id,
                "ab_test_id": test_id,
                "model": model.value,
                "response_text": result["response_text"],
                "latency_ms": result["latency_ms"],
                "tokens_used": result["tokens_used"],
                "cost_cents": cost,
            })

            return {
                "model": model.value,
                "response_text": result["response_text"],
                "latency_ms": result["latency_ms"],
                "tokens_used": result["tokens_used"],
                "cost_cents": cost,
            }
        except RuntimeError:
            # Failure — return error result
            return {
                "model": model.value,
                "response_text": f"[Error: {model.value} failed to generate a response]",
                "latency_ms": 0,
                "tokens_used": 0,
                "cost_cents": 0.0,
                "error": True,
            }

    tasks = [run_single(m) for m in models]
    results = await asyncio.gather(*tasks)

    return {
        "test_id": test_id,
        "prompt": prompt,
        "task_type": task_type.value,
        "complexity": complexity,
        "results": results,
    }


async def record_vote(test_id: str, winner_model: ModelName):
    """Record winner vote for an A/B test."""
    await execute(
        "UPDATE ab_tests SET winner_model = :winner WHERE id = :id",
        {"winner": winner_model.value, "id": test_id},
    )
