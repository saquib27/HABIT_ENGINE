# AI Financial Habit Engine 

Real-time behavioural bias detection for retail traders, with AI-powered coaching.

## Quick Start

```bash
pip install -r requirements.txt

python retrain_models.py

uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive Swagger UI.

---

## Project Structure

```
habit_engine/
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── retrain_models.py        # Regenerates corrupted PKL artifacts
├── test_engine.py           # pytest test suite
│
├── core/
│   ├── config.py            # All settings (env vars + defaults)
│   ├── engine.py            # BehavioralAlertEngine domain logic
│   ├── ai.py                # Gemini API + fallback explanations
│   └── schemas.py           # Pydantic request/response models
│
├── model/
│   ├── predictor.py         # ML inference + rule-based fallback
│   └── artifacts/           # ← place regenerated .pkl files here
│
└── routes/
    ├── trades.py            # POST /trades/analyze, GET /trades/stats
    ├── prediction.py        # POST /predict/, GET /predict/schema
    └── charts.py            # GET /charts/behavioral-breakdown, etc.
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/trades/analyze` | Analyse a trade for behavioural biases |
| GET  | `/trades/stats` | Current engine metrics |
| GET  | `/trades/history` | Recent alert history |
| POST | `/predict/` | Predict trader profile from feature vector |
| GET  | `/predict/test` | Smoke-test prediction endpoint |
| GET  | `/predict/schema` | Feature column names and order |
| GET  | `/charts/behavioral-breakdown` | Alert distribution for charting |
| GET  | `/charts/risk-profile` | Risk gauge data |
| GET  | `/charts/stats-summary` | Dashboard card data |
| GET  | `/health` | Service health + model load status |

### Example: Analyse a Trade

```bash
curl -X POST http://localhost:8000/trades/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "trade_id": "T001",
    "symbol": "RELIANCE",
    "action": "SELL",
    "quantity": 100,
    "price": 2400,
    "price_before": 2600
  }'
```

### Example: Predict Trader Profile

```bash
curl -X POST http://localhost:8000/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "avg_trades_per_day": 12,
      "win_rate": 0.38,
      "max_loss_streak": 5,
      "max_drawdown_percent": 18,
      "avg_position_size": 75000,
      "risk_per_trade_percent": 4.5,
      "trades_after_loss_ratio": 0.7,
      "holding_time_minutes": 45,
      "behavior_type_encoded": 2
    }
  }'
```

---

## PKL Corruption Fix

The original `.pkl` files were corrupted: binary data was opened in **text mode**
(`open(path, "r")`) and re-saved, replacing non-ASCII bytes with the UTF-8
replacement character (U+FFFD, `0xEFBFBD`). This is **irreversible** — the
original byte values are lost.

**Solution:** Run `python retrain_models.py` to generate fresh artifacts from
synthetic data. The script mirrors the exact feature schema extracted from the
corrupted files, so predictions will be valid once retrained on your real data.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `""` | Gemini API key (optional) |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Model name |
| `JWT_SECRET` | `CHANGE_ME` | **Change this in production** |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `PANIC_SELL_DROP_PCT` | `3.0` | % drop to trigger panic-sell alert |
| `FOMO_BUY_RISE_PCT` | `4.0` | % rise to trigger FOMO-buy alert |
| `COOLDOWN_THRESHOLD` | `75.0` | Emotional index threshold for cooldown |

---

## Running Tests

```bash
pytest test_engine.py -v
```
