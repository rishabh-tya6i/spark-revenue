from fastapi import FastAPI
from .service import router as rl_router
from ..logging_config import setup_logging

setup_logging()
app = FastAPI(title="Spark Revenue RL Agent Service")

app.include_router(rl_router, tags=["rl"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
