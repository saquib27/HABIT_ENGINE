from __future__ import annotations

import sys
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.core.engine import Trade, BehavioralAlertEngine, Alert, detect_panic_sell
from app.model.predictor import Predictor

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
def sample_trade():
    return Trade(
        trade_id="T001",
        symbol="RELIANCE",
        action="SELL",
        quantity=100,
        price=2400.0,
        timestamp=datetime.utcnow(),
    )

@pytest.fixture
def engine():
    return BehavioralAlertEngine()

class TestPanicSellDetection:
    def test_triggers_above_threshold(self, engine, sample_trade):
        price_before = 2500.0  
        alerts = engine.analyze(sample_trade, price_before)
        types = [a.alert_type for a in alerts]
        assert "PANIC SELLING" in types

    def test_does_not_trigger_below_threshold(self, engine):
        trade = Trade("T002", "TCS", "SELL", 50, 3900.0, datetime.utcnow())
        price_before = 3905.0  
        alerts = engine.analyze(trade, price_before)
        types = [a.alert_type for a in alerts]
        assert "PANIC SELLING" not in types

    def test_risk_score_scales_with_drop(self):
        trade = Trade("T003", "INFY", "SELL", 100, 1200.0, datetime.utcnow())
        alert = detect_panic_sell(trade, price_before=1320.0)  # ~9% drop
        assert alert is not None
        assert alert.emotional_risk_score > 80

class TestHabitScore:
    def test_habit_score_decreases_on_alert(self, engine):
        score_before = engine.habit_score
        trade = Trade("T010", "SBIN", "SELL", 500, 550.0, datetime.utcnow())
        engine.analyze(trade, price_before=600.0) 
        assert engine.habit_score < score_before

    def test_habit_score_increases_on_clean_trade(self, engine):
        # We need to ensure this BUY doesn't trigger CONCENTRATION RISK
        # by adding it to an already large diversified portfolio (proxy)
        engine.portfolio.holdings = {
            "STOCK1": {"quantity": 1000, "avg_price": 100.0},
            "STOCK2": {"quantity": 1000, "avg_price": 100.0},
            "STOCK3": {"quantity": 1000, "avg_price": 100.0},
        }
        engine.habit_score = 80.0
        trade = Trade("T011", "LT", "BUY", 10, 2000.0, datetime.utcnow())
        engine.analyze(trade, price_before=2001.0)  
        assert engine.habit_score > 80.0

class TestPredictor:
    def test_predict_returns_expected_keys(self):
        predictor = Predictor()
        predictor.load_models() # Should still work even without artifacts
        dummy = [0.0] * len(predictor.feature_columns)
        result = predictor.predict(dummy)
        assert "behavior" in result
        assert "discipline" in result
        assert "habit_score" in result
        assert "fallback_used" in result

    def test_rule_based_revenge_trader(self):
        predictor = Predictor()
        predictor.load_models()
        feat = {col: 0.0 for col in predictor.feature_columns}
        feat["max_loss_streak"] = 5.0
        feat["trades_after_loss_ratio"] = 0.8
        result = predictor.predict(feat)
        if result["fallback_used"]:
            assert result["behavior"] == "Revenge Trader"

@pytest.mark.anyio
async def test_ai_fallback_logic():
    from app.core.ai import get_ai_explanation
    from app.core.config import FALLBACK_EXPLANATIONS
    
    trade = Trade("T1", "RELIANCE", "SELL", 100, 2400.0, datetime.utcnow())
    alert = Alert("PANIC SELLING", "HIGH", "test", 75, trade)

    explanation = await get_ai_explanation(alert)
    assert explanation == FALLBACK_EXPLANATIONS["PANIC SELLING"]
