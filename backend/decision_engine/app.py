from fastapi import FastAPI
from .service import router
from ..logging_config import setup_logging

setup_logging()

app = FastAPI(title="AI Trading OS - Decision Engine Service")

app.include_router(router, tags=["decision"])

@app.get("/health")
async def health():
    return {"status": "healthy"}
