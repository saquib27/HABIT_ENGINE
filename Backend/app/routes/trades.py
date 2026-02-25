from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.ai import enrich_alerts_with_ai
from app.core.engine import BehavioralAlertEngine, Trade
from app.core.schemas import TradeAnalysisResponse, TradeRequest

router = APIRouter(prefix="/trades", tags=["Trade Analysis"])


def get_engine(request: Request):
    """Dependency — returns the app-level engine singleton from app state."""
    return request.app.state.engine


@router.post("/analyze", response_model=TradeAnalysisResponse, summary="Analyse a trade for behavioural biases")
async def analyze_trade(
    req: TradeRequest,
    eng: BehavioralAlertEngine = Depends(get_engine),
) -> TradeAnalysisResponse:
    trade = Trade(
        trade_id=req.trade_id,
        symbol=req.symbol,
        action=req.action,
        quantity=req.quantity,
        price=req.price,
        timestamp=datetime.utcnow(),
    )

    alerts = eng.analyze(trade, req.price_before)

    await enrich_alerts_with_ai(alerts)

    return TradeAnalysisResponse(
        alerts=[a.to_dict() for a in alerts],
        habit_score=round(eng.habit_score, 1),
        emotional_index=round(eng.emotional_index, 1),
        cooldown_recommended=eng.cooldown_recommended,
        stats=eng.get_stats(),
    )


@router.get("/stats", summary="Current engine metrics")
def get_stats(eng: BehavioralAlertEngine = Depends(get_engine)) -> dict:
    return eng.get_stats()


@router.get("/history", summary="Recent alert history")
def get_history(
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    eng: BehavioralAlertEngine = Depends(get_engine),
) -> dict:
    recent = eng.alert_history[-limit:]
    return {
        "count": len(recent),
        "alerts": [a.to_dict() for a in reversed(recent)],
    }
