from __future__ import annotations

import pickle
import numpy as np
from pathlib import Path
from sklearn.preprocessing import LabelEncoder

try:
    from xgboost import XGBClassifier, XGBRegressor
    USE_XGB = True
    print("✓ XGBoost available — training XGB models")
except ImportError:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    USE_XGB = False
    print("⚠ XGBoost not installed — training sklearn RandomForest fallback")

from app.core.config import MODEL_DIR, FEATURE_COLUMNS, BEHAVIOR_CLASSES

OUTPUT_DIR = MODEL_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DISCIPLINE_CLASSES = ["Consistent", "Impulsive", "Reckless", "Undisciplined"]

np.random.seed(42)
N = 2000

def generate_data():
    X = np.column_stack([
        np.random.exponential(5, N),        
        np.random.beta(5, 3, N),            
        np.random.randint(0, 8, N),         
        np.random.exponential(10, N),       
        np.random.exponential(50000, N), 
        np.random.exponential(2, N),        
        np.random.beta(2, 5, N),            
        np.random.exponential(120, N),      
        np.random.randint(0, 4, N),         
    ])

    behavior_labels = []
    discipline_labels = []
    habit_scores = []

    for row in X:
        trades, wr, loss_streak, drawdown, pos_size, risk_pct, tal, hold_min, _ = row
        if loss_streak >= 4 and tal >= 0.5:
            b, d, h = "Revenge Trader", "Impulsive", max(0, 35 - loss_streak * 4 + wr * 20)
        elif trades >= 10 or risk_pct >= 4:
            b, d, h = "Overtrader", "Undisciplined", max(0, 45 - trades * 1.5 + wr * 15)
        elif drawdown >= 20:
            b, d, h = "High Risk Trader", "Reckless", max(0, 50 - drawdown + wr * 20)
        else:
            b, d, h = "Disciplined", "Consistent", min(100, 60 + wr * 35)
        behavior_labels.append(b)
        discipline_labels.append(d)
        habit_scores.append(round(h + np.random.normal(0, 3), 2))

    return X, behavior_labels, discipline_labels, np.array(habit_scores)

def save(obj, filename: str):
    path = OUTPUT_DIR / filename
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=4)
    print(f"  ✓ Saved {filename} ({path.stat().st_size / 1024:.1f} KB)")

def main():
    print("\n── Generating synthetic training data ──")
    X, b_labels, d_labels, habit_scores = generate_data()
    
    le = LabelEncoder()
    le.fit(BEHAVIOR_CLASSES)
    y_behavior = le.transform(b_labels)

    le_disc = LabelEncoder()
    le_disc.fit(DISCIPLINE_CLASSES)
    y_discipline = le_disc.transform(d_labels)

    print("\n── Training models ──")
    if USE_XGB:
        behavior_model = XGBClassifier(n_estimators=100, max_depth=4, use_label_encoder=False, eval_metric="mlogloss")
        discipline_model = XGBClassifier(n_estimators=100, max_depth=4, use_label_encoder=False, eval_metric="mlogloss")
        habit_model = XGBRegressor(n_estimators=100, max_depth=4, objective="reg:squarederror")
    else:
        behavior_model = RandomForestClassifier(n_estimators=100, random_state=42)
        discipline_model = RandomForestClassifier(n_estimators=100, random_state=42)
        habit_model = RandomForestRegressor(n_estimators=100, random_state=42)

    behavior_model.fit(X, y_behavior)
    discipline_model.fit(X, y_discipline)
    habit_model.fit(X, habit_scores)

    print("\n── Saving artifacts ──")
    save(behavior_model, "behavior_model.pkl")
    save(discipline_model, "discipline_model.pkl")
    save(habit_model, "habit_model.pkl")
    save(le, "label_encoder.pkl")
    save(FEATURE_COLUMNS, "feature_columns.pkl")
    print(f"\n✅ All artifacts saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
