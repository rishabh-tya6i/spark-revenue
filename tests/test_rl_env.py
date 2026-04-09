import pytest
import numpy as np
from backend.rl.env import TradingEnv

def test_rl_env_init():
    features = np.random.randn(100, 5)
    prices = np.linspace(100, 110, 100)
    env = TradingEnv(features, prices)
    
    obs, info = env.reset()
    assert obs.shape == (6,) # 5 features + 1 position
    assert env.current_step == 0
    assert env.position == 0

def test_rl_env_step():
    features = np.random.randn(100, 5)
    prices = np.linspace(100, 110, 100)
    env = TradingEnv(features, prices)
    env.reset()
    
    # Take BUY action
    obs, reward, terminated, truncated, info = env.step(2)
    assert env.current_step == 1
    assert env.position == 1
    assert not terminated
    
    # Take SELL action
    obs, reward, terminated, truncated, info = env.step(0)
    assert env.position == -1

def test_rl_env_termination():
    features = np.random.randn(10, 5)
    prices = np.linspace(100, 110, 10)
    env = TradingEnv(features, prices, max_steps=10)
    obs, _ = env.reset()
    
    terminated = False
    for i in range(10):
        obs, reward, terminated, truncated, info = env.step(1)
        if terminated:
            break
            
    assert terminated
    assert env.current_step == 9
