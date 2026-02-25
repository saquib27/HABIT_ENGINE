from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import (
    FEATURE_COLUMNS,
    MODEL_DIR,
)

logger = logging.getLogger("HabitEngine.predictor")

_CORRUPTION_MARKER = b"\xef\xbf\xbd" 


class Predictor:
    def __init__(self):
        self._artifacts: dict[str, Any] = {}
        self.feature_columns: list[str] = FEATURE_COLUMNS
        self.models_loaded: dict[str, bool] = {
            "behavior": False,
            "discipline": False,
            "habit": False,
            "label_encoder": False,
            "feature_columns": False,
        }

    def load_models(self):
        """Load all model artifacts from disk."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        self._artifacts = {
            "behavior": self._load_artifact(MODEL_DIR / "behavior_model.pkl"),
            "discipline": self._load_artifact(MODEL_DIR / "discipline_model.pkl"),
            "habit": self._load_artifact(MODEL_DIR / "habit_model.pkl"),
            "label_encoder": self._load_artifact(MODEL_DIR / "label_encoder.pkl"),
            "feature_columns": self._load_artifact(MODEL_DIR / "feature_columns.pkl"),
        }

        self.models_loaded = {k: v is not None for k, v in self._artifacts.items()}
        
        if self._artifacts.get("feature_columns") and isinstance(self._artifacts["feature_columns"], list):
            self.feature_columns = self._artifacts["feature_columns"]

        logger.info("Predictor initialization: %s", self.models_loaded)

    def _load_artifact(self, path: Path) -> Any | None:
        if not path.exists():
            logger.warning("Artifact not found: %s — using fallback.", path)
            return None

        try:
            raw = path.read_bytes()
            if _CORRUPTION_MARKER in raw:
                logger.error("Artifact %s is corrupted (UTF-8 replacement characters found).", path.name)
                return None
            return pickle.loads(raw)
        except Exception as exc:
            logger.error("Failed to unpickle %s: %s", path.name, exc)
            return None

    def predict(self, features: list[float] | dict[str, float]) -> dict[str, Any]:
        """Predict behavior, discipline, and habit score with fallback."""
        if isinstance(features, (list, tuple, np.ndarray)):
            if len(features) != len(self.feature_columns):
                raise ValueError(f"Expected {len(self.feature_columns)} features, got {len(features)}.")
            feat_dict = dict(zip(self.feature_columns, [float(v) for v in features]))
        elif isinstance(features, dict):
            feat_dict = {col: float(features.get(col, 0)) for col in self.feature_columns}
        else:
            raise TypeError("features must be list, tuple, ndarray, or dict.")

        X = np.array([feat_dict[c] for c in self.feature_columns]).reshape(1, -1)

        behavior_model = self._artifacts.get("behavior")
        discipline_model = self._artifacts.get("discipline")
        habit_model = self._artifacts.get("habit")

        if behavior_model is None and discipline_model is None and habit_model is None:
            return self._rule_based_predict(feat_dict)

        result: dict[str, Any] = {"fallback_used": False, "input_features": feat_dict}

        # Predict Behavior
        if behavior_model:
            pred, prob = self._predict_single(behavior_model, X)
            result["behavior"] = self._decode_label(pred)
            result["behavior_confidence"] = round(float(prob), 4) if prob is not None else None
        else:
            result["behavior"] = self._rule_based_predict(feat_dict)["behavior"]
            result["behavior_confidence"] = None

        # Predict Discipline
        if discipline_model:
            pred, prob = self._predict_single(discipline_model, X)
            result["discipline"] = self._decode_label(pred)
            result["discipline_confidence"] = round(float(prob), 4) if prob is not None else None
        else:
            result["discipline"] = self._rule_based_predict(feat_dict)["discipline"]
            result["discipline_confidence"] = None

        # Predict Habit Score
        if habit_model:
            pred, prob = self._predict_single(habit_model, X)
            result["habit_score"] = round(float(pred), 2)
            result["habit_confidence"] = round(float(prob), 4) if prob is not None else None
        else:
            result["habit_score"] = self._rule_based_predict(feat_dict)["habit_score"]
            result["habit_confidence"] = None

        return result

    def _predict_single(self, model: Any, X: np.ndarray) -> tuple[Any, float | None]:
        pred = model.predict(X)[0]
        prob: float | None = None
        try:
            proba = model.predict_proba(X)[0]
            prob = float(np.max(proba))
        except Exception:
            pass
        return pred, prob

    def _decode_label(self, pred: Any) -> str:
        le = self._artifacts.get("label_encoder")
        if le is None:
            return str(pred)
        try:
            return str(le.inverse_transform([pred])[0])
        except Exception:
            return str(pred)

    def _rule_based_predict(self, features: dict[str, float]) -> dict[str, Any]:
        loss_streak = features.get("max_loss_streak", 0)
        tal_ratio = features.get("trades_after_loss_ratio", 0)
        avg_trades = features.get("avg_trades_per_day", 0)
        risk_pct = features.get("risk_per_trade_percent", 0)
        drawdown = features.get("max_drawdown_percent", 0)
        win_rate = features.get("win_rate", 0.5)

        if loss_streak >= 3 and tal_ratio >= 0.6:
            behavior, discipline, h_score = "Revenge Trader", "Impulsive", 40.0 - loss_streak * 5
        elif avg_trades >= 10 or risk_pct >= 5:
            behavior, discipline, h_score = "Overtrader", "Undisciplined", 50.0 - avg_trades * 2
        elif drawdown >= 20:
            behavior, discipline, h_score = "High Risk Trader", "Reckless", 55.0 - drawdown
        else:
            behavior, discipline, h_score = "Disciplined", "Consistent", 60.0 + win_rate * 40

        return {
            "behavior": behavior,
            "discipline": discipline,
            "habit_score": round(max(0.0, min(100.0, h_score)), 2),
            "behavior_confidence": None,
            "discipline_confidence": None,
            "habit_confidence": None,
            "fallback_used": True,
            "input_features": features,
        }
