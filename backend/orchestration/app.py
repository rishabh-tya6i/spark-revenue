from fastapi import APIRouter
from .flows import daily_training_flow

router = APIRouter()

@router.post("/orchestration/run-daily")
async def trigger_daily():
    """
    Triggers the daily master training flow.
    Currently synchronous for v1.
    """
    results = daily_training_flow()
    return {"status": "completed", "results": results}
