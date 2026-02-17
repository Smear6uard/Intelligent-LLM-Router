import json
import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from models import (
    ClassifyRequest, CompletionRequest, ABTestRequest, VoteRequest,
    ClassificationResult, CompletionMetadata, ModelName,
)
from classifier import classify
from router import select_model, calculate_cost, calculate_hypothetical_cost, FALLBACK_ORDER
from gateway import stream_completion, generate_completion
from database import init_db, close_db, insert_request, fetch_one
from ab_testing import run_ab_test, get_ab_models, record_vote
from analytics import (
    get_summary, get_timeseries, get_model_distribution,
    get_cost_comparison, get_recent, get_ab_history,
)
from seed import seed_database
import config
import gateway_live

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory rate limiter
_rate_limit: dict[str, list[float]] = {}


def _get_rate_limit_params() -> tuple[int, int]:
    """Return (window_seconds, max_requests) based on current mode."""
    if config.get_mode() == "live":
        return config.LIVE_RATE_LIMIT_WINDOW, config.LIVE_RATE_LIMIT_MAX
    return config.DEMO_RATE_LIMIT_WINDOW, config.DEMO_RATE_LIMIT_MAX


def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window, max_req = _get_rate_limit_params()
    if client_ip not in _rate_limit:
        _rate_limit[client_ip] = []
    # Prune old entries
    _rate_limit[client_ip] = [t for t in _rate_limit[client_ip] if now - t < window]
    if len(_rate_limit[client_ip]) >= max_req:
        return False
    _rate_limit[client_ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.load_env()
    await init_db()
    count = await seed_database()
    if count:
        logger.info(f"Seeded {count} requests")
    else:
        logger.info("Database already seeded")
    logger.info(f"Starting in {config.get_mode().upper()} mode")
    yield
    await close_db()


app = FastAPI(
    title="Intelligent LLM Router",
    description="Routes prompts to the optimal LLM based on complexity analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        if not check_rate_limit(client_ip):
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return await call_next(request)


# --- Mode ---

@app.get("/api/mode")
async def mode():
    return await config.get_mode_info()


# --- Classification ---

@app.post("/api/classify")
async def classify_prompt(req: ClassifyRequest):
    result = classify(req.prompt)
    model, reason = select_model(result["task_type"], result["complexity"])

    return ClassificationResult(
        task_type=result["task_type"],
        complexity=result["complexity"],
        confidence=result["confidence"],
        signals=result["signals"],
        recommended_model=model,
        routing_reason=reason,
    )


# --- Completion ---

@app.post("/api/completion")
async def completion(req: CompletionRequest):
    classification = classify(req.prompt)
    task_type = classification["task_type"]
    complexity = classification["complexity"]
    confidence = classification["confidence"]

    # Use override model or route automatically
    was_routed = req.model is None
    if req.model:
        model = req.model
        reason = "User-specified model override"
    else:
        model, reason = select_model(task_type, complexity)

    # Check spend cap before live calls
    current_mode = config.get_mode()
    if current_mode == "live":
        under_cap = await config.check_spend_cap()
        if not under_cap:
            current_mode = "demo"
            logger.info("Spend cap hit — falling back to DEMO for this request")

    request_id = str(uuid.uuid4())

    if req.stream:
        return StreamingResponse(
            _stream_response(request_id, req.prompt, task_type, complexity, confidence, model, reason, was_routed, current_mode),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return await _non_stream_response(request_id, req.prompt, task_type, complexity, confidence, model, reason, was_routed, current_mode)


async def _stream_response(request_id, prompt, task_type, complexity, confidence, model, reason, was_routed, current_mode):
    # Send metadata first
    metadata = CompletionMetadata(
        request_id=request_id,
        task_type=task_type,
        complexity=complexity,
        confidence=confidence,
        model=model,
        routing_reason=reason,
        was_routed=was_routed,
    )
    yield f"event: metadata\ndata: {metadata.model_dump_json()}\n\n"

    # Choose gateway based on mode
    if current_mode == "live":
        api_key = config.get_api_key()
        stream_fn = gateway_live.stream_completion_live(prompt, model, api_key)
    else:
        stream_fn = stream_completion(task_type, model)

    try:
        full_text = ""
        final_data = None

        async for chunk in stream_fn:
            if chunk["type"] == "chunk":
                full_text += chunk["content"]
                yield f"event: chunk\ndata: {json.dumps({'content': chunk['content']})}\n\n"
            elif chunk["type"] == "done":
                final_data = chunk

        if final_data:
            cost = calculate_cost(model, final_data["tokens_used"])
            await insert_request({
                "id": request_id,
                "prompt": prompt,
                "task_type": task_type.value,
                "complexity": complexity,
                "confidence": confidence,
                "model": model.value,
                "was_routed": 1 if was_routed else 0,
                "response_text": final_data["response_text"],
                "latency_ms": final_data["latency_ms"],
                "tokens_used": final_data["tokens_used"],
                "cost_cents": cost,
            })

            yield f"event: done\ndata: {json.dumps({'latency_ms': final_data['latency_ms'], 'tokens_used': final_data['tokens_used'], 'cost_cents': cost})}\n\n"

    except RuntimeError:
        # Try fallback model
        fallback = FALLBACK_ORDER.get(model)
        if fallback:
            yield f"event: chunk\ndata: {json.dumps({'content': f'[Retrying with {fallback.value}...] '})}\n\n"

            if current_mode == "live":
                api_key = config.get_api_key()
                fallback_stream = gateway_live.stream_completion_live(prompt, fallback, api_key)
            else:
                fallback_stream = stream_completion(task_type, fallback)

            async for chunk in fallback_stream:
                if chunk["type"] == "chunk":
                    yield f"event: chunk\ndata: {json.dumps({'content': chunk['content']})}\n\n"
                elif chunk["type"] == "done":
                    cost = calculate_cost(fallback, chunk["tokens_used"])
                    await insert_request({
                        "id": request_id,
                        "prompt": prompt,
                        "task_type": task_type.value,
                        "complexity": complexity,
                        "confidence": confidence,
                        "model": fallback.value,
                        "was_routed": 1 if was_routed else 0,
                        "response_text": chunk["response_text"],
                        "latency_ms": chunk["latency_ms"],
                        "tokens_used": chunk["tokens_used"],
                        "cost_cents": cost,
                    })
                    yield f"event: done\ndata: {json.dumps({'latency_ms': chunk['latency_ms'], 'tokens_used': chunk['tokens_used'], 'cost_cents': cost})}\n\n"


async def _non_stream_response(request_id, prompt, task_type, complexity, confidence, model, reason, was_routed, current_mode):
    try:
        if current_mode == "live":
            api_key = config.get_api_key()
            result = await gateway_live.generate_completion_live(prompt, model, api_key)
        else:
            result = await generate_completion(task_type, model)
    except RuntimeError:
        fallback = FALLBACK_ORDER.get(model)
        if not fallback:
            raise HTTPException(status_code=503, detail="Model unavailable")
        model = fallback
        reason = f"Fallback: {reason}"
        if current_mode == "live":
            api_key = config.get_api_key()
            result = await gateway_live.generate_completion_live(prompt, model, api_key)
        else:
            result = await generate_completion(task_type, model)

    cost = calculate_cost(model, result["tokens_used"])

    await insert_request({
        "id": request_id,
        "prompt": prompt,
        "task_type": task_type.value,
        "complexity": complexity,
        "confidence": confidence,
        "model": model.value,
        "was_routed": 1 if was_routed else 0,
        "response_text": result["response_text"],
        "latency_ms": result["latency_ms"],
        "tokens_used": result["tokens_used"],
        "cost_cents": cost,
    })

    return {
        "metadata": CompletionMetadata(
            request_id=request_id,
            task_type=task_type,
            complexity=complexity,
            confidence=confidence,
            model=model,
            routing_reason=reason,
            was_routed=was_routed,
        ).model_dump(),
        "response_text": result["response_text"],
        "latency_ms": result["latency_ms"],
        "tokens_used": result["tokens_used"],
        "cost_cents": cost,
    }


# --- A/B Testing ---

@app.post("/api/ab-test")
async def ab_test(req: ABTestRequest):
    classification = classify(req.prompt)
    task_type = classification["task_type"]
    complexity = classification["complexity"]

    models = get_ab_models(task_type, req.models)
    result = await run_ab_test(req.prompt, task_type, complexity, models)

    return result


@app.post("/api/ab-test/{test_id}/vote")
async def vote(test_id: str, req: VoteRequest):
    test = await fetch_one("SELECT id FROM ab_tests WHERE id = :id", {"id": test_id})
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    await record_vote(test_id, req.winner_model)
    return {"status": "ok", "test_id": test_id, "winner": req.winner_model.value}


# --- Analytics ---

@app.get("/api/analytics/summary")
async def analytics_summary():
    return await get_summary()


@app.get("/api/analytics/timeseries")
async def analytics_timeseries(days: int = 7):
    return await get_timeseries(days)


@app.get("/api/analytics/model-distribution")
async def analytics_model_distribution():
    return await get_model_distribution()


@app.get("/api/analytics/cost-comparison")
async def analytics_cost_comparison():
    return await get_cost_comparison()


@app.get("/api/analytics/recent")
async def analytics_recent(limit: int = 20):
    return await get_recent(limit)


@app.get("/api/ab-tests/history")
async def ab_tests_history(limit: int = 20):
    return await get_ab_history(limit)


# --- Health ---

@app.get("/health")
async def health():
    return {"status": "ok", "mode": config.get_mode()}
