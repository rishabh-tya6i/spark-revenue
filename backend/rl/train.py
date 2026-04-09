import os
import logging
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from .env import TradingEnv
from .utils import load_rl_data, set_global_seeds
from ..db import SessionLocal
from ..config import settings

logger = logging.getLogger(__name__)

def train_rl_agent(symbol: str, interval: str, episodes: int = None):
    """
    Trains a PPO agent on the TradingEnv.
    """
    logger.info(f"Starting RL training for {symbol} ({interval})")
    
    # 1. Load data
    with SessionLocal() as session:
        features, prices = load_rl_data(session, symbol, interval)
    
    if features.size == 0:
        logger.error("No data found for RL training.")
        return None

    # 2. Setup environment
    num_episodes = episodes or settings.RL_TRAINING_EPISODES
    max_steps = settings.RL_MAX_STEPS_PER_EPISODE
    
    def make_env():
        return TradingEnv(
            features=features,
            prices=prices,
            initial_capital=settings.RL_INITIAL_CAPITAL,
            transaction_cost_bps=settings.RL_TRANSACTION_COST_BPS,
            max_steps=max_steps
        )

    env = DummyVecEnv([make_env])
    
    # 3. Initialize Agent (PPO)
    # Using a simple MLP policy for v1
    model = PPO(
        "MlpPolicy", 
        env, 
        verbose=1,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        seed=42
    )
    
    # 4. Train
    total_timesteps = num_episodes * max_steps
    logger.info(f"Training for {total_timesteps} total timesteps...")
    model.learn(total_timesteps=total_timesteps)
    
    # 5. Save model
    os.makedirs(settings.RL_AGENT_MODEL_DIR, exist_ok=True)
    model_path = os.path.join(settings.RL_AGENT_MODEL_DIR, f"{symbol}_{interval}_ppo.zip")
    model.save(model_path)
    
    logger.info(f"RL model saved to {model_path}")
    return model_path
