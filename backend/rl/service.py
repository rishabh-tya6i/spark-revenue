from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
import os
import logging
import numpy as np
from stable_baselines3 import PPO

from ..db import SessionLocal, OhlcBar, PriceFeature
from ..config import settings
from .utils import load_rl_data

logger = logging.getLogger(__name__)

router = APIRouter()

class RLActionRequest(BaseModel):
    symbol: str
    interval: str = "5m"

class RLActionResponse(BaseModel):
    symbol: str
    interval: str
    action: Literal["BUY", "SELL", "HOLD"]
    action_index: int
    confidence: Optional[float] = None
    policy_version: Optional[str] = None

# Model Cache
_rl_model_cache = {}

def get_rl_model(symbol: str, interval: str):
    cache_key = f"{symbol}_{interval}"
    if cache_key not in _rl_model_cache:
        model_path = os.path.join(settings.RL_AGENT_MODEL_DIR, f"{symbol}_{interval}_ppo.zip")
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"RL Model not found for {cache_key}")
        
        _rl_model_cache[cache_key] = PPO.load(model_path)
        logger.info(f"Loaded RL model from {model_path}")
    
    return _rl_model_cache[cache_key]

@router.post("/rl/action", response_model=RLActionResponse)
async def get_rl_action(request: RLActionRequest):
    symbol = request.symbol
    interval = request.interval

    # 1. Fetch latest state
    with SessionLocal() as session:
        # We need latest features. Reuse load_rl_data logic for consistency.
        # But we only need the LAST timestep.
        features, _ = load_rl_data(session, symbol, interval)
        
        if features.size == 0:
            raise HTTPException(status_code=400, detail="Not enough feature history for RL inference")

        last_feat = features[-1]
        # Current position for stateless inference is 0 (flat)
        obs = np.append(last_feat, 0.0).astype(np.float32)

    # 2. Predict Action
    model = get_rl_model(symbol, interval)
    action_idx, _states = model.predict(obs, deterministic=True)
    
    action_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
    
    return RLActionResponse(
        symbol=symbol,
        interval=interval,
        action=action_map[int(action_idx)],
        action_index=int(action_idx),
        policy_version="v1"
    )
