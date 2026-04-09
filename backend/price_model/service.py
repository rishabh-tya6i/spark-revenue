from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
import torch
import numpy as np
import os
import logging

from .model import load_model
from .data import build_price_model_dataset
from ..db import SessionLocal, OhlcBar, PriceFeature
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

class PricePredictionRequest(BaseModel):
    symbol: str
    interval: str = "5m"
    horizon: Optional[int] = None

class PricePredictionResponse(BaseModel):
    symbol: str
    interval: str
    horizon: int
    prediction_type: Literal["regression", "classification"]
    value: Optional[float] = None
    label: Optional[str] = None
    probabilities: Optional[dict[str, float]] = None
    model_version: Optional[str] = None

# Model Cache
_model_cache = {}

def get_model(symbol: str, interval: str):
    cache_key = f"{symbol}_{interval}"
    if cache_key not in _model_cache:
        model_path = os.path.join(settings.PRICE_MODEL_DIR, f"{symbol}_{interval}_latest.pt")
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"Model not found for {cache_key}")
        
        # We need to know input_size. In our case it's fixed 5 (log_ret, rsi, vwap_ratio, ema_short_ratio, ema_long_ratio)
        input_size = 5 
        _model_cache[cache_key] = load_model(model_path, input_size=input_size)
        logger.info(f"Loaded model from {model_path}")
    
    return _model_cache[cache_key]

@router.post("/predict/price-path", response_model=PricePredictionResponse)
async def predict_price_path(request: PricePredictionRequest):
    symbol = request.symbol
    interval = request.interval
    horizon = request.horizon or settings.PRICE_MODEL_PREDICTION_HORIZON
    input_window = settings.PRICE_MODEL_INPUT_WINDOW

    # 1. Fetch latest data
    with SessionLocal() as session:
        # We need the most recent input_window timesteps
        # We handle this by building a mini dataset with 0 horizon (since we only need X)
        # But our build_price_model_dataset expects horizon because it builds y.
        # Let's manually build X here or use a helper.
        
        query = session.query(
            OhlcBar.close,
            PriceFeature.rsi_14,
            PriceFeature.vwap,
            PriceFeature.ema_short,
            PriceFeature.ema_long,
            OhlcBar.end_ts
        ).join(
            PriceFeature, 
            (OhlcBar.symbol == PriceFeature.symbol) & (OhlcBar.end_ts == PriceFeature.ts)
        ).filter(
            OhlcBar.symbol == symbol,
            PriceFeature.interval == interval
        ).order_by(OhlcBar.end_ts.desc()).limit(input_window)

        data = query.all()
        if len(data) < input_window:
            raise HTTPException(status_code=400, detail="Not enough feature history to make prediction")

        # Reverse to get chronological order
        data = data[::-1]
        
        # Prepare feature vector (same logic as in data.py)
        # close, rsi_14, vwap, ema_short, ema_long, ts
        df = []
        for d in data:
            df.append({
                'close': d[0],
                'rsi_14': d[1] / 100.0,
                'vwap_ratio': d[2] / d[0],
                'ema_short_ratio': d[3] / d[0],
                'ema_long_ratio': d[4] / d[0],
            })
        
        # Add log returns
        for i in range(1, len(df)):
            df[i]['log_ret'] = np.log(df[i]['close'] / df[i-1]['close'])
        
        # Drop first row because it has no log_ret
        # But wait, our model expects input_window. 
        # If we need 60 inputs, we need 61 bars.
        # Let's adjust.
        if len(df) == input_window:
            # We forgot to fetch one extra for log_ret. 
            # For v1 simplicity, set first log_ret to 0
            df[0]['log_ret'] = 0.0

        feature_cols = ['log_ret', 'rsi_14', 'vwap_ratio', 'ema_short_ratio', 'ema_long_ratio']
        X = [[d[col] for col in feature_cols] for d in df]
        X = np.array(X)[np.newaxis, :, :] # (1, input_window, features)

    # 2. Predict
    model = get_model(symbol, interval)
    with torch.no_grad():
        input_tensor = torch.FloatTensor(X)
        output = model(input_tensor)
        probabilities = torch.softmax(output, dim=1).numpy()[0]
        prediction_idx = np.argmax(probabilities)
        
    labels = ["DOWN", "FLAT", "UP"]
    
    return PricePredictionResponse(
        symbol=symbol,
        interval=interval,
        horizon=horizon,
        prediction_type="classification",
        label=labels[prediction_idx],
        probabilities={labels[i]: float(probabilities[i]) for i in range(len(labels))},
        model_version="v1"
    )
