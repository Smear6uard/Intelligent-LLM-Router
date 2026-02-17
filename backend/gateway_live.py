import time
import logging
import httpx
from models import ModelName

logger = logging.getLogger(__name__)

# Map internal model names to OpenRouter model IDs
OPENROUTER_MODEL_MAP: dict[ModelName, str] = {
    ModelName.CLAUDE_3_5_SONNET: "anthropic/claude-3.5-sonnet",
    ModelName.GPT_4O:            "openai/gpt-4o",
    ModelName.GEMINI_1_5_PRO:    "google/gemini-pro-1.5",
    ModelName.DEEPSEEK_V3:       "deepseek/deepseek-chat",
    ModelName.GPT_4O_MINI:       "openai/gpt-4o-mini",
    ModelName.CLAUDE_3_HAIKU:    "anthropic/claude-3-haiku",
}

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=120.0)
    return _client


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://llm-router.dev",
        "X-Title": "Intelligent LLM Router",
    }


async def generate_completion_live(
    prompt: str,
    model: ModelName,
    api_key: str,
) -> dict:
    """Non-streaming call to OpenRouter. Returns {response_text, latency_ms, tokens_used}."""
    openrouter_model = OPENROUTER_MODEL_MAP.get(model)
    if not openrouter_model:
        raise RuntimeError(f"No OpenRouter mapping for model {model.value}")

    client = _get_client()
    payload = {
        "model": openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    start = time.time()
    resp = await client.post(OPENROUTER_URL, json=payload, headers=_headers(api_key))
    latency_ms = int((time.time() - start) * 1000)

    if resp.status_code != 200:
        logger.error(f"OpenRouter error {resp.status_code}: {resp.text[:200]}")
        raise RuntimeError(f"OpenRouter API error: {resp.status_code}")

    data = resp.json()
    response_text = data["choices"][0]["message"]["content"]
    tokens_used = data.get("usage", {}).get("total_tokens", 0)
    if not tokens_used:
        # Estimate if usage not provided
        tokens_used = max(10, int(len(response_text.split()) * 1.3))

    return {
        "response_text": response_text,
        "latency_ms": latency_ms,
        "tokens_used": tokens_used,
    }


async def stream_completion_live(
    prompt: str,
    model: ModelName,
    api_key: str,
):
    """Async generator yielding chunks in the same shape as the mock gateway.
    Yields: {type: "chunk", content: str} and finally {type: "done", response_text, latency_ms, tokens_used}
    """
    openrouter_model = OPENROUTER_MODEL_MAP.get(model)
    if not openrouter_model:
        raise RuntimeError(f"No OpenRouter mapping for model {model.value}")

    client = _get_client()
    payload = {
        "model": openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    start = time.time()
    full_text = ""
    tokens_used = 0

    async with client.stream("POST", OPENROUTER_URL, json=payload, headers=_headers(api_key)) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            logger.error(f"OpenRouter stream error {resp.status_code}: {body[:200]}")
            raise RuntimeError(f"OpenRouter API error: {resp.status_code}")

        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                break

            try:
                import json
                chunk_data = json.loads(data_str)
            except Exception:
                continue

            # Extract content delta
            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                full_text += content
                yield {"type": "chunk", "content": content}

            # Check for usage in the final chunk
            usage = chunk_data.get("usage")
            if usage:
                tokens_used = usage.get("total_tokens", tokens_used)

    latency_ms = int((time.time() - start) * 1000)

    if not tokens_used:
        tokens_used = max(10, int(len(full_text.split()) * 1.3))

    yield {
        "type": "done",
        "response_text": full_text,
        "latency_ms": latency_ms,
        "tokens_used": tokens_used,
    }
