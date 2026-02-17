import os
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Rate limit settings per mode
DEMO_RATE_LIMIT_WINDOW = 60     # seconds
DEMO_RATE_LIMIT_MAX = 30
LIVE_RATE_LIMIT_WINDOW = 3600   # 1 hour
LIVE_RATE_LIMIT_MAX = 20

# Spend cap
DAILY_SPEND_CAP_CENTS = 200.0   # $2.00

# Internal state
_openrouter_api_key: str | None = None
_forced_demo = False
_forced_demo_date: date | None = None


def load_env():
    """Load .env file from backend directory (no dependency needed)."""
    global _openrouter_api_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key == "OPENROUTER_API_KEY" and value:
                    _openrouter_api_key = value
                    logger.info("OpenRouter API key loaded from .env")

    # Also check environment variable (Docker / system env override)
    env_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if env_key:
        _openrouter_api_key = env_key
        logger.info("OpenRouter API key loaded from environment")

    if _openrouter_api_key:
        logger.info("LIVE mode available")
    else:
        logger.info("No API key found — running in DEMO mode")


def get_api_key() -> str | None:
    return _openrouter_api_key


def get_mode() -> str:
    """Returns 'live' or 'demo'."""
    global _forced_demo, _forced_demo_date

    if not _openrouter_api_key:
        return "demo"

    # Reset forced demo flag on new day
    if _forced_demo and _forced_demo_date != date.today():
        _forced_demo = False
        _forced_demo_date = None
        logger.info("New day — spend cap reset, LIVE mode re-enabled")

    if _forced_demo:
        return "demo"

    return "live"


async def check_spend_cap() -> bool:
    """Check if today's spend is under the daily cap.
    Returns True if under cap (ok to proceed). Sets forced demo if over."""
    global _forced_demo, _forced_demo_date
    from database import fetch_one

    row = await fetch_one(
        "SELECT COALESCE(SUM(cost_cents), 0) AS total "
        "FROM requests WHERE created_at >= date('now')"
    )
    spent = row["total"] if row else 0.0

    if spent >= DAILY_SPEND_CAP_CENTS:
        if not _forced_demo:
            _forced_demo = True
            _forced_demo_date = date.today()
            logger.warning(
                f"Daily spend cap hit ({spent:.1f}c >= {DAILY_SPEND_CAP_CENTS:.1f}c) — switching to DEMO mode"
            )
        return False
    return True


async def get_mode_info() -> dict:
    """Full mode status for the /api/mode endpoint."""
    from database import fetch_one

    mode = get_mode()

    row = await fetch_one(
        "SELECT COALESCE(SUM(cost_cents), 0) AS total "
        "FROM requests WHERE created_at >= date('now')"
    )
    spend_today = row["total"] if row else 0.0

    reason = "api_key_present" if _openrouter_api_key else "no_api_key"
    if _forced_demo and _openrouter_api_key:
        reason = "spend_cap_reached"

    # Calculate requests remaining for live rate limit
    requests_remaining = None
    if mode == "live":
        requests_remaining = LIVE_RATE_LIMIT_MAX  # approximate; real tracking is in main.py

    return {
        "mode": mode,
        "reason": reason,
        "spend_today_cents": round(spend_today, 2),
        "spend_cap_cents": DAILY_SPEND_CAP_CENTS,
        "requests_remaining": requests_remaining,
    }
