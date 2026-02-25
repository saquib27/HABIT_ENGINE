import os
from pathlib import Path

# /Backend/app/core/config.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "app" / "model" / "artifacts"

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT: int = int(os.getenv("GEMINI_TIMEOUT", "10"))

JWT_SECRET: str = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

APP_TITLE: str = "AI Financial Habit Engine"
APP_VERSION: str = "3.0.0"
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

PANIC_SELL_DROP_PCT: float = float(os.getenv("PANIC_SELL_DROP_PCT", "3.0"))
FOMO_BUY_RISE_PCT: float = float(os.getenv("FOMO_BUY_RISE_PCT", "4.0"))
COOLDOWN_EMOTIONAL_INDEX: float = float(os.getenv("COOLDOWN_THRESHOLD", "75.0"))
RECENT_TRADE_WINDOW: int = 200  # rolling window size

FEATURE_COLUMNS: list[str] = [
    "avg_trades_per_day",
    "win_rate",
    "max_loss_streak",
    "max_drawdown_percent",
    "avg_position_size",
    "risk_per_trade_percent",
    "trades_after_loss_ratio",
    "holding_time_minutes",
    "behavior_type_encoded",
]

BEHAVIOR_CLASSES: list[str] = [
    "Disciplined",
    "High Risk Trader",
    "Overtrader",
    "Revenge Trader",
]

FALLBACK_EXPLANATIONS = {
    "PANIC SELLING": "This trade followed a sharp price drop, suggesting an emotional reaction to loss. Consider setting a pre-defined stop-loss to avoid manual panic selling.",
    "FOMO BUYING": "This trade followed a price surge, suggesting a fear of missing out. Avoid chasing green candles; wait for a pullback or consolidation.",
    "CONCENTRATION RISK": "A large portion of your capital is now in one asset. This increases vulnerability to specific news. Consider diversifying to manage risk.",
}
