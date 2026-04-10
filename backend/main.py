from fastapi import FastAPI
from .logging_config import setup_logging

from .backtesting.service import router as backtest_router
from .decision_engine.service import router as decision_router
from .sentiment.service import router as sentiment_router
from .options_intel.service import router as options_router
from .price_model.service import router as price_router
from .rl.service import router as rl_router
from .orchestration.app import router as orchestration_router
from .execution.app import router as execution_router

setup_logging()
app = FastAPI(title="Spark Revenue AI Trading OS Backend")

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

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
