import logging
from typing import List, Optional
from prefect import flow, task
from .utils import get_train_symbols, get_train_interval
from ..price_model.train import train_price_model
from ..rl.train import train_rl_agent

logger = logging.getLogger(__name__)

@task(name="Train Price Model Task")
def train_price_model_task(symbol: str, interval: str, epochs: int = 10):
    try:
        logger.info(f"Starting Price Model training task for {symbol}")
        model_path = train_price_model(symbol, interval, epochs=epochs)
        return model_path
    except Exception as e:
        logger.error(f"Failed to train Price Model for {symbol}: {e}")
        return None

@task(name="Train RL Agent Task")
def train_rl_agent_task(symbol: str, interval: str, episodes: int = None):
    try:
        logger.info(f"Starting RL Agent training task for {symbol}")
        model_path = train_rl_agent(symbol, interval, episodes=episodes)
        return model_path
    except Exception as e:
        logger.error(f"Failed to train RL Agent for {symbol}: {e}")
        return None

@flow(name="Train Price Models Flow")
def train_price_models_flow(symbols: Optional[List[str]] = None, interval: Optional[str] = None, epochs: int = 10):
    train_symbols = symbols or get_train_symbols()
    train_interval = interval or get_train_interval()
    
    logger.info(f"Starting Price Model training flow for symbols: {train_symbols}")
    results = []
    for symbol in train_symbols:
        res = train_price_model_task(symbol, train_interval, epochs=epochs)
        results.append(res)
    return results

@flow(name="Train RL Agents Flow")
def train_rl_agents_flow(symbols: Optional[List[str]] = None, interval: Optional[str] = None, episodes: Optional[int] = None):
    train_symbols = symbols or get_train_symbols()
    train_interval = interval or get_train_interval()
    
    logger.info(f"Starting RL Agent training flow for symbols: {train_symbols}")
    results = []
    for symbol in train_symbols:
        res = train_rl_agent_task(symbol, train_interval, episodes=episodes)
        results.append(res)
    return results

@flow(name="Daily Training Master Flow")
def daily_training_flow():
    logger.info("Starting Daily Training Master Flow")
    
    price_results = train_price_models_flow()
    rl_results = train_rl_agents_flow()
    
    return {
        "price_models": price_results,
        "rl_agents": rl_results
    }

if __name__ == "__main__":
    daily_training_flow()
