from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .token_store import (
    clear_upstox_token,
    get_upstox_token_status,
    set_upstox_token,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class UpstoxTokenIn(BaseModel):
    token: str


@router.get("/upstox-token")
def upstox_token_status():
    status = get_upstox_token_status()
    return {"present": status.present, "masked": status.masked, "source": status.source}


@router.post("/upstox-token")
def upstox_token_set(payload: UpstoxTokenIn):
    try:
        set_upstox_token(payload.token)
        status = get_upstox_token_status()
        return {"status": "ok", "present": status.present, "masked": status.masked, "source": status.source}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/upstox-token")
def upstox_token_clear():
    try:
        clear_upstox_token()
        status = get_upstox_token_status()
        return {"status": "ok", "present": status.present, "masked": status.masked, "source": status.source}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

