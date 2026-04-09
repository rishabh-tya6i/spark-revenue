from fastapi import FastAPI
from .service import router as price_router
from ..logging_config import setup_logging

setup_logging()
app = FastAPI(title="Spark Revenue Price Prediction Service")

app.include_router(price_router, tags=["prediction"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
