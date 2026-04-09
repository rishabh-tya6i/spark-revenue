from fastapi import FastAPI
from .service import router as sentiment_router
from ..logging_config import setup_logging

setup_logging()
app = FastAPI(title="Spark Revenue Sentiment Service")

app.include_router(sentiment_router, tags=["sentiment"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
