"""
Pydantic request and response models.

All validation lives here — routes stay thin.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


class TradeRequest(BaseModel):
    trade_id: str = Field(..., min_length=1, description="Unique trade identifier")
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock ticker (e.g. RELIANCE)")
    action: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Number of shares (must be positive)")
    price: float = Field(..., gt=0, description="Execution price in ₹")
    price_before: float = Field(..., gt=0, description="Price immediately before trade in ₹")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ("BUY", "SELL"):
            raise ValueError("action must be 'BUY' or 'SELL'")
        return v

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, v: str) -> str:
        return v.upper().strip()


class AlertResponse(BaseModel):
    type: str
    severity: str
    risk_score: int
    message: str
    ai_explanation: str
    symbol: str
    action: str
    quantity: float
    price: float
    time: str


class TradeAnalysisResponse(BaseModel):
    alerts: list[AlertResponse]
    habit_score: float
    emotional_index: float
    cooldown_recommended: bool
    stats: dict[str, Any]


class PredictRequest(BaseModel):
    """
    Accepts either:
      - `features` as a list of floats (ordered to match feature_columns), OR
      - `features` as a dict {column_name: value}
    """
    features: Union[list[float], dict[str, float]] = Field(
        ...,
        description=(
            "Feature vector — either an ordered list matching feature_columns, "
            "or a dict of {column_name: value}."
        ),
    )


class PredictResponse(BaseModel):
    behavior: Optional[str]
    discipline: Optional[str]
    habit_score: Optional[float]
    behavior_confidence: Optional[float]
    discipline_confidence: Optional[float]
    habit_confidence: Optional[float]
    fallback_used: bool
    input_features: Union[dict[str, float], list[float]]


class HealthResponse(BaseModel):
    status: str
    version: str
    gemini_enabled: bool
    models_loaded: dict[str, bool]
    engine_active: bool
