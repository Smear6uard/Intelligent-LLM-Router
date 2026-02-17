from database import fetch_all, fetch_one
from router import EXPENSIVE_MODEL_COST


async def get_summary() -> dict:
    """Aggregate stats: total requests, costs, savings, etc."""
    row = await fetch_one("""
        SELECT
            COUNT(*) as total_requests,
            COALESCE(SUM(cost_cents), 0) as total_cost_cents,
            COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
            COALESCE(AVG(complexity), 0) as avg_complexity,
            COUNT(DISTINCT model) as models_used,
            COALESCE(SUM(tokens_used), 0) as total_tokens
        FROM requests
    """)

    today_row = await fetch_one("""
        SELECT COUNT(*) as cnt FROM requests
        WHERE date(created_at) = date('now')
    """)

    total_cost = row["total_cost_cents"]
    total_tokens = row["total_tokens"]
    hypothetical_cost = round(EXPENSIVE_MODEL_COST * total_tokens / 1000, 4)
    savings = round((1 - total_cost / hypothetical_cost) * 100, 1) if hypothetical_cost > 0 else 0

    return {
        "total_requests": row["total_requests"],
        "total_cost_cents": round(total_cost, 2),
        "avg_latency_ms": round(row["avg_latency_ms"], 1),
        "avg_complexity": round(row["avg_complexity"], 1),
        "hypothetical_cost_cents": round(hypothetical_cost, 2),
        "cost_savings_percent": savings,
        "models_used": row["models_used"],
        "requests_today": today_row["cnt"],
    }


async def get_timeseries(days: int = 7) -> list[dict]:
    """Time-bucketed request counts, avg latency, and cost per day."""
    rows = await fetch_all(f"""
        SELECT
            date(created_at) as day,
            COUNT(*) as requests,
            ROUND(AVG(latency_ms), 1) as avg_latency_ms,
            ROUND(SUM(cost_cents), 4) as total_cost_cents
        FROM requests
        WHERE created_at >= datetime('now', '-{days} days')
        GROUP BY date(created_at)
        ORDER BY day ASC
    """)
    return rows


async def get_model_distribution() -> list[dict]:
    """Model usage percentages."""
    rows = await fetch_all("""
        SELECT
            model,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM requests), 1) as percentage
        FROM requests
        GROUP BY model
        ORDER BY count DESC
    """)
    return rows


async def get_cost_comparison() -> dict:
    """Actual costs vs hypothetical (always-use-expensive-model) costs per model."""
    actual = await fetch_all("""
        SELECT
            model,
            SUM(tokens_used) as total_tokens,
            ROUND(SUM(cost_cents), 4) as actual_cost
        FROM requests
        GROUP BY model
        ORDER BY actual_cost DESC
    """)

    total_actual = sum(r["actual_cost"] for r in actual)
    total_tokens = sum(r["total_tokens"] for r in actual)
    hypothetical = round(EXPENSIVE_MODEL_COST * total_tokens / 1000, 4)

    return {
        "by_model": actual,
        "total_actual_cents": round(total_actual, 2),
        "total_hypothetical_cents": round(hypothetical, 2),
        "savings_cents": round(hypothetical - total_actual, 2),
        "savings_percent": round((1 - total_actual / hypothetical) * 100, 1) if hypothetical > 0 else 0,
    }


async def get_recent(limit: int = 20) -> list[dict]:
    """Recent requests for the dashboard table."""
    rows = await fetch_all(f"""
        SELECT
            id, prompt, task_type, complexity, confidence,
            model, latency_ms, tokens_used, cost_cents, created_at
        FROM requests
        ORDER BY created_at DESC
        LIMIT {limit}
    """)
    # Truncate prompt for display
    for row in rows:
        if row["prompt"] and len(row["prompt"]) > 80:
            row["prompt"] = row["prompt"][:80] + "..."
    return rows


async def get_ab_history(limit: int = 20) -> list[dict]:
    """A/B test history with results."""
    tests = await fetch_all(f"""
        SELECT id, prompt, task_type, complexity, models, winner_model, created_at
        FROM ab_tests
        ORDER BY created_at DESC
        LIMIT {limit}
    """)

    for test in tests:
        results = await fetch_all("""
            SELECT model, latency_ms, tokens_used, cost_cents
            FROM ab_results
            WHERE ab_test_id = :test_id
        """, {"test_id": test["id"]})
        test["results"] = results
        if test["prompt"] and len(test["prompt"]) > 80:
            test["prompt"] = test["prompt"][:80] + "..."

    return tests
