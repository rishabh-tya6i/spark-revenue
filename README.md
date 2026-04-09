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

### 11. Desktop App (Electron + React, v1)

The Desktop App provides a unified command center for visualizing the fused decisions, market data, sentiment, and options signals from the backend services.

#### Key Features
- **Dashboard**: High-level view for a selected symbol (e.g., BTCUSDT) showing the latest fused decision, confidence scores, sentiment headlines, and options indicators (PCR, Max Pain).
- **Backtesting UI**: Configuration form to run historical simulations and view performance metrics (Win Rate, Sharpe, Max Drawdown) in a clean dashboard.
- **Alerts Feed**: Real-time list of system-generated alerts triggered when high-confidence signals are detected.
- **Cross-Platform**: Built with Electron, compatible with macOS, Windows, and Linux.

#### Setup & Run
1. **Prerequisites**: Ensure the backend services are running (default `http://localhost:8000`).
2. **Install Dependencies**:
   ```bash
   cd desktop
   npm install
   cd renderer
   npm install
   ```
3. **Run in Development Mode**:
   ```bash
   cd desktop
   npm run dev
   ```
4. **Run Tests**:
   ```bash
   cd desktop
   npm run test
   ```

#### Tech Stack
- **Electron**: Desktop shell.
- **React + TypeScript**: UI development.
- **Vite**: Modern frontend bundling.
- **Axios**: API communication.
- **Vitest + RTL**: Unit testing.

### 12. Running with Docker

You can spin up the entire backend infrastructure (Postgres, Redis, MLflow, and the unified Backend API) using Docker Compose.

#### Prerequisites
- Docker and Docker Compose installed.

#### Steps
1. **Environment Setup**:
   Ensure `.env` exists at the root (copy from `.env.example`).
   ```bash
   cp .env.example .env
   ```
2. **Launch Services**:
   ```bash
   docker compose up --build
   ```
3. **Verify**:
   - Backend API: `http://localhost:8000/health`
   - MLflow UI: `http://localhost:5000`
   - Postgres: `localhost:5432`
   - Redis: `localhost:6379`

### 13. Continuous Integration (CI)

This repository includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that automatically runs tests on every push and pull request to `main` or `master`.

- **Backend Job**: Installs dependencies (`pip install .[test]`) and runs Python tests using `pytest` with an in-memory SQLite database.
- **Frontend Job**: Installs dependencies in `desktop/renderer` and runs frontend unit tests using `vitest`.
 
### 14. Training & Orchestration (Prefect v1)
 
The orchestration layer automates the recurring tasks of data processing and model retraining using Prefect.
 
#### Key Features
- **Automated Workflows**: Prefect-based flows for retraining both LSTM Price Models and RL Agents across multiple symbols.
- **Unified Master Flow**: A `daily_training_flow` that sequences model training tasks, suitable for scheduling via cron or Prefect Cloud.
- **CLI & API**: Trigger training flows via the command line or through a dedicated REST API endpoint.
- **MLflow Integration**: All training tasks are automatically tracked in MLflow for metric comparison and artifact management.
 
#### CLI Usage
```bash
# Train price models for specific symbols
python -m backend.orchestration.cli train-price-models --symbols BTCUSDT,ETHUSDT --epochs 10

# Train RL agents
python -m backend.orchestration.cli train-rl-agents --symbols BTCUSDT --episodes 50

# Run the full daily training pipeline
python -m backend.orchestration.cli run-daily
```
 
#### API Endpoint
- `POST /orchestration/run-daily`: Synchronously triggers the master training flow.
 
#### Configuration
Adjust orchestration settings in `.env`:
- `TRAIN_SYMBOLS`: Comma-separated list of symbols to include in automated training.
- `TRAIN_DEFAULT_INTERVAL`: Timeframe to use for training data (e.g., `5m`).
- `TRAIN_DAILY_RUN_HOUR_UTC`: Preferred hour for the daily master flow.
