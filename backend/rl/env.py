import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TradingEnv(gym.Env):
    """
    Custom Trading Environment for RL.
    Actions: 0: SELL, 1: HOLD, 2: BUY
    Observatons: [features..., position]
    """
    metadata = {"render_modes": ["human"]}

    def __init__(
        self, 
        features: np.ndarray, 
        prices: np.ndarray, 
        initial_capital: float = 100000.0,
        transaction_cost_bps: float = 10.0,
        max_steps: int = 500
    ):
        super(TradingEnv, self).__init__()
        
        self.features = features
        self.prices = prices
        self.initial_capital = initial_capital
        self.transaction_cost_pct = transaction_cost_bps / 10000.0
        self.max_steps = min(max_steps, len(features) - 1)
        
        # Action space: 0: SELL, 1: HOLD, 2: BUY
        self.action_space = spaces.Discrete(3)
        
        # Observation space: features + current position (-1, 0, 1)
        num_features = features.shape[1]
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(num_features + 1,), 
            dtype=np.float32
        )
        
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.current_step = 0
        self.position = 0 # 0: Flat, 1: Long, -1: Short
        self.cash = self.initial_capital
        self.holdings = 0.0
        self.portfolio_value = self.initial_capital
        
        return self._get_observation(), {}

    def _get_observation(self):
        obs = np.append(self.features[self.current_step], float(self.position))
        return obs.astype(np.float32)

    def step(self, action):
        # 1. Update Portfolio based on Action
        # Action 0: SELL, 1: HOLD, 2: BUY
        
        prev_portfolio_value = self.portfolio_value
        current_price = self.prices[self.current_step]
        
        new_position = self.position
        if action == 0: # SELL
            new_position = -1
        elif action == 2: # BUY
            new_position = 1
        # Action 1 is HOLD (stay in current position)
        
        # If position changes, apply transaction costs
        if new_position != self.position:
            # For simplicity, we assume we transition to exactly 1 position unit of the asset 
            # (or -1 for short). In a more complex env, we'd handle quantity.
            # Trade size is approximately our total portfolio value.
            trade_cost = self.portfolio_value * self.transaction_cost_pct
            self.cash -= trade_cost
            self.position = new_position

        # 2. Update Portfolio Value based on Price Move
        # PnL = position * (Price_t - Price_t-1)
        if self.current_step > 0:
            price_change = self.prices[self.current_step] - self.prices[self.current_step - 1]
            # If position is 1, we gain. If -1, we gain on price decrease.
            pnl = self.position * price_change * (self.initial_capital / self.prices[0]) # Normalized quantity
            self.portfolio_value += pnl
        
        # 3. Increment Step
        self.current_step += 1
        
        # 4. Check Termination
        terminated = self.current_step >= self.max_steps
        truncated = False # Can be used for time limits if current_step < max_steps but limit reached
        
        # 5. Calculate Reward (Incremental Returns)
        # reward = (PV_t - PV_t-1) / PV_t-1
        reward = (self.portfolio_value - prev_portfolio_value) / prev_portfolio_value if prev_portfolio_value > 0 else 0
        
        # 6. Get Next Obs
        obs = self._get_observation() if not terminated else np.zeros(self.observation_space.shape, dtype=np.float32)
        
        info = {
            "step": self.current_step,
            "portfolio_value": self.portfolio_value,
            "position": self.position
        }
        
        return obs, float(reward), terminated, truncated, info
