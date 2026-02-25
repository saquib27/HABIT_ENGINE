from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT, FALLBACK_EXPLANATIONS

if TYPE_CHECKING:
    from app.core.engine import Alert

logger = logging.getLogger("HabitEngine.ai")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={{api_key}}"
)

_cache: dict[str, str] = {}


def _build_prompt(alert: "Alert") -> str:
    t = alert.trade
    return (
        f"You are a behavioural finance coach helping Indian retail investors.\n\n"
        f"Alert Type : {alert.alert_type}\n"
        f"Risk Score : {alert.emotional_risk_score}/100\n"
        f"Trade      : {t.action} {t.quantity} shares of {t.symbol} @ ₹{t.price:.2f}\n\n"
        f"In 4 concise sentences:\n"
        f"1. Name the specific cognitive bias at play.\n"
        f"2. Explain why this behaviour is financially harmful.\n"
        f"3. Give one actionable, practical tip to avoid it next time.\n"
        f"4. Encourage the trader with empathy — avoid being preachy."
    )


async def get_ai_explanation(alert: "Alert") -> str:
    """
    Return an AI-generated explanation for the alert.
    Uses in-memory cache keyed by (alert_type, symbol, risk_decile).
    Falls back to static text if Gemini is not configured or errors out.
    """
    cached = _cache.get(alert.cache_key)
    if cached:
        return cached

    if not GEMINI_API_KEY:
        return FALLBACK_EXPLANATIONS.get(alert.alert_type, "No explanation available.")

    payload = {"contents": [{"parts": [{"text": _build_prompt(alert)}]}]}
    url = GEMINI_URL.format(api_key=GEMINI_API_KEY)

    try:
        async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            text: str = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            _cache[alert.cache_key] = text
            return text

    except httpx.TimeoutException:
        logger.warning("Gemini API timed out for alert %s", alert.alert_type)
    except httpx.HTTPStatusError as exc:
        logger.error("Gemini API HTTP error %s: %s", exc.response.status_code, exc)
    except (KeyError, IndexError):
        logger.error("Unexpected Gemini response structure for %s", alert.alert_type)
    except Exception as exc:
        logger.error("Gemini API unexpected error: %s", exc)

    fallback = FALLBACK_EXPLANATIONS.get(alert.alert_type, "No explanation available.")
    return fallback


async def enrich_alerts_with_ai(alerts: list["Alert"]) -> None:
    """Concurrently fetch AI explanations for a list of alerts (in-place)."""
    if not alerts:
        return
    explanations = await asyncio.gather(
        *[get_ai_explanation(a) for a in alerts], return_exceptions=True
    )
    for alert, explanation in zip(alerts, explanations):
        if isinstance(explanation, Exception):
            logger.error("AI enrichment failed for %s: %s", alert.alert_type, explanation)
            alert.ai_explanation = FALLBACK_EXPLANATIONS.get(alert.alert_type, "")
        else:
            alert.ai_explanation = explanation
