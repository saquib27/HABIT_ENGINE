from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request

from app.core.schemas import PredictRequest, PredictResponse
from app.model.predictor import Predictor

router = APIRouter(prefix="/predict", tags=["ML Prediction"])


def get_predictor(request: Request):
    return request.app.state.predictor


@router.post("/", response_model=PredictResponse, summary="Predict trader profile from feature vector")
def predict_endpoint(
    req: PredictRequest,
    predictor: Predictor = Depends(get_predictor)
) -> PredictResponse:
    try:
        result = predictor.predict(req.features)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PredictResponse(**result)


@router.get("/test", response_model=PredictResponse, summary="Smoke-test prediction with zero vector")
def test_prediction(predictor: Predictor = Depends(get_predictor)) -> PredictResponse:
    dummy = [0.0] * len(predictor.feature_columns) if predictor.feature_columns else [0.0]
    result = predictor.predict(dummy)
    return PredictResponse(**result)


@router.get("/schema", summary="Return expected feature columns in canonical order")
def get_schema(predictor: Predictor = Depends(get_predictor)) -> dict:
    return {
        "feature_columns": predictor.feature_columns,
        "count": len(predictor.feature_columns),
        "note": (
            "Pass features as an ordered list (same length as feature_columns) "
            "or as a dict {column_name: value}.  Missing dict keys default to 0."
        ),
    }
