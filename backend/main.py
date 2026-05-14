from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .logging_config import setup_logging
from .config import settings

from .backtesting.service import router as backtest_router
from .decision_engine.service import router as decision_router
from .sentiment.service import router as sentiment_router
from .options_intel.service import router as options_router
from .price_model.service import router as price_router
from .rl.service import router as rl_router
from .orchestration.app import router as orchestration_router
from .execution.app import router as execution_router
from .instruments.app import router as instruments_router
from .ingestion.app import router as ingestion_router
from .settings.app import router as settings_router

setup_logging()
app = FastAPI(title="Spark Revenue AI Trading OS Backend")

# CORS (desktop renderer runs on http://localhost:5173 in dev; Electron may use file://)
cors_raw = (settings.CORS_ALLOW_ORIGINS or "").strip()
if cors_raw == "*":
    cors_allow_origins = ["*"]
else:
    cors_allow_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In unified mode, we might want to group them or keep them root.
# Given they don't have overlapping paths (mostly /backtest, /decision, /sentiment, /options, /predict, /rl), prefixing is optional but good for organization.

app.include_router(backtest_router, tags=["backtest"])
app.include_router(decision_router, tags=["decision"])
app.include_router(sentiment_router, tags=["sentiment"])
app.include_router(options_router, tags=["options"])
app.include_router(price_router, tags=["prediction"])
app.include_router(rl_router, tags=["rl"])
app.include_router(orchestration_router, tags=["orchestration"])
app.include_router(execution_router, tags=["execution"])
app.include_router(instruments_router, tags=["instruments"])
app.include_router(ingestion_router, tags=["ingestion"])
app.include_router(settings_router, tags=["settings"])

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
