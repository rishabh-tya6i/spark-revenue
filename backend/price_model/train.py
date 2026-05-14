import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import mlflow
import os
import logging
import numpy as np
from contextlib import nullcontext
from .data import build_price_model_dataset
from .model import create_model, save_model
from ..db import SessionLocal
from ..config import settings

logger = logging.getLogger(__name__)

def train_price_model(symbol: str, interval: str, epochs: int = 10, batch_size: int = 32):
    """
    Trains the LSTM model for a given symbol and interval.
    """
    logger.info(f"Starting training for {symbol} ({interval})")
    
    # 1. Load data
    with SessionLocal() as session:
        X, y = build_price_model_dataset(
            session, 
            symbol, 
            interval, 
            settings.PRICE_MODEL_INPUT_WINDOW, 
            settings.PRICE_MODEL_PREDICTION_HORIZON
        )
    
    if X.size == 0:
        logger.error("No data found for training.")
        return

    # 2. Split data (Time-series split)
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    # 3. Create DataLoaders
    train_ds = TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train))
    val_ds = TensorDataset(torch.FloatTensor(X_val), torch.LongTensor(y_val))
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)
    
    # 4. Initialize model, loss, optimizer
    input_size = X.shape[2]
    model = create_model(input_size=input_size)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # 5. MLflow Tracking
    mlflow_enabled = True
    try:
        mlflow.set_experiment("PricePrediction_LSTM")
        run_ctx = mlflow.start_run()
    except Exception as e:
        mlflow_enabled = False
        run_ctx = nullcontext()
        logger.warning(f"MLflow tracking disabled for this run: {e}")

    with run_ctx:
        if mlflow_enabled:
            mlflow.log_params({
                "symbol": symbol,
                "interval": interval,
                "input_window": settings.PRICE_MODEL_INPUT_WINDOW,
                "prediction_horizon": settings.PRICE_MODEL_PREDICTION_HORIZON,
                "epochs": epochs,
                "batch_size": batch_size,
                "num_features": input_size
            })
        
        best_val_loss = float('inf')
        model_path = os.path.join(settings.PRICE_MODEL_DIR, f"{symbol}_{interval}_latest.pt")
        
        for epoch in range(epochs):
            model.train()
            train_loss = 0.0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            avg_train_loss = train_loss / len(train_loader)
            
            # Validation
            model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    outputs = model(batch_X)
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()
                    
                    _, predicted = torch.max(outputs.data, 1)
                    total += batch_y.size(0)
                    correct += (predicted == batch_y).sum().item()
            
            avg_val_loss = val_loss / len(val_loader)
            val_acc = correct / total if total > 0 else 0
            
            logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}, Val Acc: {val_acc:.4f}")
            if mlflow_enabled:
                mlflow.log_metric("train_loss", avg_train_loss, step=epoch)
                mlflow.log_metric("val_loss", avg_val_loss, step=epoch)
                mlflow.log_metric("val_accuracy", val_acc, step=epoch)
            
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                save_model(model, model_path)
                logger.info(f"Best model saved to {model_path}")
                if mlflow_enabled:
                    mlflow.log_artifact(model_path)

    return model_path
