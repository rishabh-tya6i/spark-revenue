from fastapi import FastAPI
from .service import router

app = FastAPI(title="AI Trading OS - Options Intelligence Service")

app.include_router(router, tags=["options"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "options_intelligence"}
