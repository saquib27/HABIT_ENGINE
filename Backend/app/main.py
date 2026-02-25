import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import APP_TITLE, APP_VERSION, CORS_ORIGINS, GEMINI_API_KEY
from app.core.engine import BehavioralAlertEngine
from app.core.schemas import HealthResponse
from app.model.predictor import Predictor
from app.routes.trades import router as trades_router
from app.routes.prediction import router as prediction_router
from app.routes.charts import router as charts_router

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("HabitEngine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles model loading and engine initialization.
    """
    logger.info("Starting up HabitEngine...")
    
    # Initialize Engine Singleton
    app.state.engine = BehavioralAlertEngine()
    
    # Initialize Predictor and load models
    predictor = Predictor()
    predictor.load_models()
    app.state.predictor = predictor
    
    logger.info("HabitEngine startup complete.")
    yield
    logger.info("Shutting down HabitEngine...")


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "Detects emotional trading biases (panic selling, FOMO, overtrading) "
        "in real-time and provides AI-powered behavioural coaching."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# Include Routers
app.include_router(trades_router)
app.include_router(prediction_router)
app.include_router(charts_router)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health(request: Request) -> HealthResponse:
    """Comprehensive health check for models, API, and engine."""
    predictor: Predictor = request.app.state.predictor
    engine_active = hasattr(request.app.state, "engine") and request.app.state.engine is not None
    
    all_models_loaded = all(predictor.models_loaded.values())
    
    return HealthResponse(
        status="running" if all_models_loaded else "degraded (rule-based fallback active)",
        version=APP_VERSION,
        gemini_enabled=bool(GEMINI_API_KEY),
        models_loaded=predictor.models_loaded,
        engine_active=engine_active,
    )


@app.get("/", tags=["System"])
def root() -> dict:
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
