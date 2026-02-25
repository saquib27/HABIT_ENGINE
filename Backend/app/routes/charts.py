from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request

from app.core.engine import BehavioralAlertEngine
from app.model.predictor import Predictor

router = APIRouter(prefix="/charts", tags=["Charts & Analytics"])


def get_engine(request: Request):
    return request.app.state.engine


def get_predictor(request: Request):
    return request.app.state.predictor


def _build_alert_chart(alert_history: list) -> dict:
    """Aggregate alert counts by type for a bar/pie chart."""
    counts: dict[str, int] = {}
    for alert in alert_history:
        counts[alert.alert_type] = counts.get(alert.alert_type, 0) + 1

    labels = list(counts.keys()) or ["No Alerts"]
    values = list(counts.values()) or [0]

    return {
        "chart_type": "bar",
        "title": "Behavioural Alert Breakdown",
        "labels": labels,
        "values": values,
        "colors": {
            "PANIC SELLING": "#EF4444",
            "FOMO BUYING": "#F59E0B",
            "OVERTRADING": "#8B5CF6",
            "REVENGE TRADING": "#EC4899",
            "CONCENTRATION RISK": "#3B82F6",
        },
    }


def _build_prediction_chart(prediction: dict) -> dict:
    """Convert a prediction result into gauge-friendly chart data."""
    habit = prediction.get("habit_score") or 0

    # In a real app, these would be separate regression heads or part of a multi-label output
    return {
        "chart_type": "radial",
        "title": "Risk Profile",
        "labels": ["Habit Score"],
        "values": [round(habit, 1)],
        "max": 100,
    }


@router.get("/behavioral-breakdown", summary="Alert type distribution for charting")
def behavioral_breakdown(eng: BehavioralAlertEngine = Depends(get_engine)) -> dict:
    return _build_alert_chart(eng.alert_history)


@router.get("/risk-profile", summary="Build chart data from a prediction result")
def risk_profile(
    predictor: Predictor = Depends(get_predictor),
    avg_trades_per_day: float = 5.0,
    win_rate: float = 0.5,
    max_loss_streak: float = 2.0,
    max_drawdown_percent: float = 10.0,
    avg_position_size: float = 50000.0,
    risk_per_trade_percent: float = 2.0,
    trades_after_loss_ratio: float = 0.3,
    holding_time_minutes: float = 120.0,
    behavior_type_encoded: float = 0.0,
) -> dict:
    feat = {
        "avg_trades_per_day": avg_trades_per_day,
        "win_rate": win_rate,
        "max_loss_streak": max_loss_streak,
        "max_drawdown_percent": max_drawdown_percent,
        "avg_position_size": avg_position_size,
        "risk_per_trade_percent": risk_per_trade_percent,
        "trades_after_loss_ratio": trades_after_loss_ratio,
        "holding_time_minutes": holding_time_minutes,
        "behavior_type_encoded": behavior_type_encoded,
    }

    try:
        prediction = predictor.predict(feat)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "prediction": prediction,
        "chart": _build_prediction_chart(prediction),
    }


@router.get("/stats-summary", summary="Engine metrics formatted for dashboard cards")
def stats_summary(eng: BehavioralAlertEngine = Depends(get_engine)) -> dict:
    stats = eng.get_stats()
    return {
        "cards": [
            {"label": "Habit Score", "value": stats["habit_score"], "unit": "/100", "color": "green"},
            {"label": "Emotional Index", "value": stats["emotional_index"], "unit": "/100", "color": "orange"},
            {"label": "Total Alerts", "value": stats["total_alerts"], "unit": "", "color": "red"},
            {"label": "Trades Analysed", "value": stats["total_trades_analysed"], "unit": "", "color": "blue"},
            {"label": "Open Positions", "value": stats["portfolio_positions"], "unit": "", "color": "purple"},
        ],
        "cooldown_banner": stats["cooldown_recommended"],
    }
