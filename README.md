# Spark Revenue - AI Trading OS

This is the backend for the AI Trading OS, focusing on market data ingestion and processing.

## Project Structure

- `backend/`: Core backend package.
  - `config.py`: Configuration management using Pydantic Settings.
  - `db.py`: Database connection and SQLAlchemy models.
  - `logging_config.py`: Structured JSON logging setup.
  - `ingestion/`: Market data ingestion module.
    - `zerodha_client.py`: Client for Zerodha Kite API (Currently Stubbed).
    - `binance_client.py`: Client for Binance API (Currently Stubbed).
    - `ohlc_ingestor.py`: Logic for historical and live data ingestion.
    - `cli.py`: Command Line Interface for data operations.
- `alembic/`: Database migration scripts.
- `tests/`: Unit and integration tests.

## Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL (for production/development)
- Kafka (for live feeds)

### 2. Environment Setup
Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[test]"
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your details:
```bash
cp .env.example .env
```

### 4. Database Migrations
Run the migrations to create the database schema:
```bash
# Ensure DATABASE_URL in .env is correct
alembic upgrade head
```

## Usage

### Historical Backfill CLI
You can use the ingestion CLI to backfill historical data. Note that current implementations of Zerodha and Binance clients use **stub data**.

```bash
# Backfill Zerodha data
python -m backend.ingestion.cli backfill --source zerodha --symbol NIFTY --start 2024-01-01 --end 2024-01-31 --interval 5m

# Backfill Binance data
python -m backend.ingestion.cli backfill --source binance --symbol BTCUSDT --start 2024-01-01 --end 2024-01-31 --interval 5m
```

## Feature Store (Price Features)

The `feature_store` module computes and manages technical features for trading models.

### Computed Features (v1)
- **RSI (14)**: Relative Strength Index.
- **VWAP**: Cumulative Volume Weighted Average Price.
- **EMA (12/26)**: Exponential Moving Averages for short and long trends.

### Feature Backfill CLI
Once you have OHLC data ingested, you can compute price features for a historical range:

```bash
python -m backend.feature_store.cli features-backfill --symbol BTCUSDT --start 2024-01-01 --end 2024-01-31 --interval 5m
```

### Online Feature Store (Redis)
Latest features are automatically cached in Redis with a TTL (default 300s). This allows for high-frequency access to model inputs without hitting the database.

## Development

### Running Tests
```bash
pytest
```
Tests for the feature store use `fakeredis` to avoid the need for a live Redis server during CI/CD.

## Price Prediction Model (LSTM v1)

The `price_model` module implements a PyTorch-based LSTM model for near-term price directional prediction.

### Model Details
- **Architecture**: 1-2 LSTM layers with a final fully connected layer.
- **Target**: 3-class classification (DOWN, FLAT, UP) based on a log-return threshold over a future horizon.
- **Inputs**: 60 timesteps (configurable) of features including log returns, RSI, VWAP ratio, and EMA ratios.
- **Tracking**: Integrated with **MLflow** for experiment tracking and metric logging.

### Training the Model
To train the model for a specific symbol:
```bash
python -m backend.price_model.cli price-model-train --symbol BTCUSDT --interval 5m --epochs 10
```

### Inference Service
The inference service provides a REST API for real-time predictions.

Start the service:
```bash
uvicorn backend.price_model.app:app --port 8001 --reload
```

Predict endpoint:
```bash
curl -X POST http://localhost:8001/predict/price-path \
     -H "Content-Type: application/json" \
     -d '{"symbol": "BTCUSDT", "interval": "5m"}'
```

## RL Agent (v1)

The `rl` module implements a Reinforcement Learning agent for trading policy generation.

### Agent Details
- **Algorithm**: Proximal Policy Optimization (**PPO**) from Stable-Baselines3.
- **Action Space**: `SELL`, `HOLD`, `BUY`.
- **Observation Space**: Feature vector (log returns, RSI, VWAP/EMA ratios) joined with the agent's current position.
- **Reward Function**: Incremental portfolio returns corrected for transaction costs.

### Training the RL Agent
To train the agent for a symbol:
```bash
python -m backend.rl.cli rl-train --symbol BTCUSDT --interval 5m
```

### Action Recommendation Service
The RL service provides real-time action recommendations based on the trained policy.

Start the service:
```bash
uvicorn backend.rl.app:app --port 8002 --reload
```

Action endpoint:
```bash
curl -X POST http://localhost:8002/rl/action \
     -H "Content-Type: application/json" \
     -d '{"symbol": "BTCUSDT", "interval": "5m"}'
```

## Development
...
# spark-revenue

### 8. Options Intelligence Engine (v1)

The Options Intelligence module provides advanced derivatives analysis by processing option chain data to derive market sentiment and structural levels.

#### Key Features
*   **Metrics**: Calculates Put-Call Ratio (PCR) and Max Pain strikes.
*   **Signals**: Identifies "CALL_BUILDUP" and "PUT_BUILDUP" based on OI concentration and PCR trends.
*   **Ingestion**: Supports synthetic (stubbed) options chain generation for development.
*   **API**: Real-time snapshot refreshing and signal retrieval.

#### CLI Usage
*   **Snapshot Ingestion**: `python -m backend.options_intel.cli options-snapshot --symbol NIFTY --expiry 2024-12-26`
*   **Signal Calculation**: `python -m backend.options_intel.cli options-signal --symbol NIFTY --expiry 2024-12-26`

#### API Endpoints
*   `POST /options/refresh-snapshot`: Ingests latest data and returns new signals.
*   `GET /options/signal`: Retrieves the most recent computed signals for a symbol.

### 9. Decision Engine + Alerts (v1)

The Decision Engine acts as the central brain of the system, fusing inputs from all other modules (Price Model, RL Agent, Sentiment, and Options) into a single confidence-scored decision.

#### Key Features
*   **Signal Fusion**: Combines multi-modal signals using a weighted heuristic to produce a decision label (`STRONG_BULLISH` to `STRONG_BEARISH`) and a normalized score.
*   **Automated Alerting**: Triggers alerts when decision confidence crosses the `DECISION_MIN_CONFIDENCE` threshold.
*   **Persistence**: Stores every fused decision and triggered alert in Postgres for auditing and UI display.

#### CLI Usage
*   **Compute Decision**: `python -m backend.decision_engine.cli decision-compute --symbol BTCUSDT --interval 5m`
*   **Recent Alerts**: `python -m backend.decision_engine.cli alerts-recent --symbol BTCUSDT`

#### API Endpoints
*   `POST /decision/compute`: Triggers a fresh fusion cycle and returns the decision + optional alert.
*   `GET /decision/latest`: Returns the most recent fused decision for a symbol.
*   `GET /alerts/recent`: Returns a list of recent alerts across all symbols.

### 10. Backtesting Engine (v1)

The Backtesting Engine allows for the historical simulation of trading strategies using stored OHLC data. It tracks PnL, calculate risk metrics, and persists results for analysis.

#### Key Features
*   **Historical Replay**: Iterates through past OHLC bars to simulate step-by-step decision making.
*   **Pluggable Strategies**: Base interface for implementing rule-based or model-driven strategies.
*   **Performance Metrics**: Automatically calculates Win Rate, Max Drawdown, and annualized Sharpe Ratio.
*   **Execution Simulation**: Accounts for transaction costs (BPS) and slippage (via spread/commission modeling).

#### CLI Usage
*   **Run Backtest**: `python -m backend.backtesting.cli backtest-run --symbol BTCUSDT --start-ts 2024-01-01 --end-ts 2024-01-07`
*   **Show Results**: `python -m backend.backtesting.cli backtest-show --run-id 1`

#### API Endpoints
*   `POST /backtest/run`: Initiates a new backtest run for a specific symbol and timeframe.
*   `GET /backtest/run/{run_id}`: Retrieves the status and basic info of a backtest.
*   `GET /backtest/metrics/{run_id}`: Retrieves detailed performance metrics for a completed run.
