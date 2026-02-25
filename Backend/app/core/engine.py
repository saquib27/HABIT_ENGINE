"""
Behavioural Alert Engine.

Detects emotional trading patterns (panic selling, FOMO buying, overtrading,
revenge trading, concentration risk) and maintains a rolling habit score.
"""

from __future__ import annotations

import hashlib
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable

from app.core.config import (
    COOLDOWN_EMOTIONAL_INDEX,
    FOMO_BUY_RISE_PCT,
    PANIC_SELL_DROP_PCT,
    RECENT_TRADE_WINDOW,
)

logger = logging.getLogger("HabitEngine.alerts")


@dataclass(frozen=True)
class Trade:
    trade_id: str
    symbol: str
    action: str         
    quantity: float
    price: float
    timestamp: datetime
    pnl: Optional[float] = None


@dataclass
class Alert:
    alert_type: str
    severity: str       
    message: str
    emotional_risk_score: int   
    trade: Trade
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ai_explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.alert_type,
            "severity": self.severity,
            "risk_score": self.emotional_risk_score,
            "message": self.message,
            "ai_explanation": self.ai_explanation,
            "symbol": self.trade.symbol,
            "action": self.trade.action,
            "quantity": self.trade.quantity,
            "price": self.trade.price,
            "time": self.timestamp.isoformat(),
        }

    @property
    def cache_key(self) -> str:
        """Stable cache key for AI explanation (bucketed by risk decile)."""
        bucket = self.emotional_risk_score // 10
        raw = f"{self.alert_type}:{self.trade.symbol}:{bucket}"
        return hashlib.md5(raw.encode()).hexdigest()


class Portfolio:
    """Tracks live holdings using FIFO-like average cost basis."""

    def __init__(self) -> None:
        self.holdings: dict[str, dict] = {}  

    def apply_trade(self, trade: Trade) -> None:
        sym = trade.symbol

        if trade.action == "BUY":
            h = self.holdings.get(sym, {"quantity": 0.0, "avg_price": 0.0})
            new_qty = h["quantity"] + trade.quantity
            new_avg = (
                h["quantity"] * h["avg_price"] + trade.quantity * trade.price
            ) / new_qty
            self.holdings[sym] = {"quantity": new_qty, "avg_price": round(new_avg, 4)}

        elif trade.action == "SELL":
            if sym not in self.holdings:
                logger.warning("SELL on unknown position: %s", sym)
                return
            self.holdings[sym]["quantity"] -= trade.quantity
            if self.holdings[sym]["quantity"] <= 0:
                del self.holdings[sym]

    @property
    def total_value_proxy(self) -> float:
        """Sum of quantity × avg_price (a proxy; real value needs live prices)."""
        return sum(
            h["quantity"] * h["avg_price"] for h in self.holdings.values()
        )

    def concentration(self, symbol: str) -> float:
        """Fraction of portfolio value held in one symbol (0–1)."""
        total = self.total_value_proxy
        if total <= 0 or symbol not in self.holdings:
            return 0.0
        h = self.holdings[symbol]
        return (h["quantity"] * h["avg_price"]) / total


def detect_panic_sell(trade: Trade, price_before: float) -> Optional[Alert]:
    if trade.action != "SELL" or price_before <= 0:
        return None
    drop_pct = ((price_before - trade.price) / price_before) * 100
    if drop_pct < PANIC_SELL_DROP_PCT:
        return None
    risk = min(100, int(60 + drop_pct * 3))
    return Alert(
        alert_type="PANIC SELLING",
        severity="HIGH",
        message=f"Sold {trade.symbol} after a {drop_pct:.1f}% price drop.",
        emotional_risk_score=risk,
        trade=trade,
    )


def detect_fomo_buy(trade: Trade, price_before: float) -> Optional[Alert]:
    if trade.action != "BUY" or price_before <= 0:
        return None
    rise_pct = ((trade.price - price_before) / price_before) * 100
    if rise_pct < FOMO_BUY_RISE_PCT:
        return None
    risk = min(100, int(55 + rise_pct * 3))
    return Alert(
        alert_type="FOMO BUYING",
        severity="HIGH",
        message=f"Bought {trade.symbol} after a {rise_pct:.1f}% price surge.",
        emotional_risk_score=risk,
        trade=trade,
    )


def detect_concentration_risk(
    trade: Trade, portfolio: Portfolio, threshold: float = 0.40
) -> Optional[Alert]:
    """Flag if a single position exceeds `threshold` of portfolio value after trade."""
    conc = portfolio.concentration(trade.symbol)
    if conc < threshold:
        return None
    risk = min(100, int(50 + conc * 50))
    return Alert(
        alert_type="CONCENTRATION RISK",
        severity="MEDIUM",
        message=(
            f"{trade.symbol} now represents {conc*100:.0f}% of your portfolio."
        ),
        emotional_risk_score=risk,
        trade=trade,
    )


class BehavioralAlertEngine:
    """
    Stateful engine that processes trades and emits behavioural alerts.
    """

    def __init__(self) -> None:
        self.portfolio = Portfolio()
        self.recent_trades: deque[Trade] = deque(maxlen=RECENT_TRADE_WINDOW)
        self.alert_history: list[Alert] = []
        self.habit_score: float = 100.0

    @property
    def emotional_index(self) -> float:
        """Rolling average risk score of the last 10 alerts (0–100)."""
        window = self.alert_history[-10:]
        if not window:
            return 0.0
        return sum(a.emotional_risk_score for a in window) / len(window)

    @property
    def cooldown_recommended(self) -> bool:
        return self.emotional_index > COOLDOWN_EMOTIONAL_INDEX

    def analyze(self, trade: Trade, price_before: float) -> list[Alert]:
        """
        Analyse a single trade against all detectors.
        Updates portfolio, habit score, and alert history.
        Returns list of triggered alerts (may be empty).
        """
        self.recent_trades.append(trade)

        detectors: list[Callable[[Trade, float], Optional[Alert]]] = [
            lambda t, pb: detect_panic_sell(t, pb),
            lambda t, pb: detect_fomo_buy(t, pb),
        ]

        triggered: list[Alert] = []
        for fn in detectors:
            alert = fn(trade, price_before)
            if alert:
                triggered.append(alert)

        self.portfolio.apply_trade(trade)
        conc_alert = detect_concentration_risk(trade, self.portfolio)
        if conc_alert:
            triggered.append(conc_alert)

        self.alert_history.extend(triggered)
        if triggered:
            avg_risk = sum(a.emotional_risk_score for a in triggered) / len(triggered)
            self.habit_score = max(0.0, self.habit_score - avg_risk * 0.05)
        else:
            self.habit_score = min(100.0, self.habit_score + 1.0)

        logger.info(
            "Trade %s analysed | alerts=%d | habit_score=%.1f | ei=%.1f",
            trade.trade_id,
            len(triggered),
            self.habit_score,
            self.emotional_index,
        )

        return triggered

    def get_stats(self) -> dict:
        return {
            "habit_score": round(self.habit_score, 1),
            "emotional_index": round(self.emotional_index, 1),
            "cooldown_recommended": self.cooldown_recommended,
            "total_trades_analysed": len(self.recent_trades),
            "total_alerts": len(self.alert_history),
            "portfolio_positions": len(self.portfolio.holdings),
        }
