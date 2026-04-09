from fastapi import FastAPI
from .service import router
from ..logging_config import setup_logging

setup_logging()

app = FastAPI(title="AI Trading OS - Backtesting Service")

app.include_router(router, tags=["backtest"])

@app.get("/health")
async def health():
    return {"status": "healthy"}
