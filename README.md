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
You can use the ingestion CLI to backfill historical data.

```bash
# Backfill Upstox data (Requires instrument sync first)
python -m backend.ingestion.cli backfill --source upstox --symbol NIFTY --start 2024-05-01 --end 2024-05-15 --interval 5m

# Backfill Zerodha data (Stubbed)
python -m backend.ingestion.cli backfill --source zerodha --symbol NIFTY --start 2024-01-01 --end 2024-01-31 --interval 5m

# Backfill Binance data (Stubbed)
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
 
### 15. Execution & Paper Trading (v1)
 
The execution engine provides a simulated environment for paper trading based on decisions and RL actions produced by the system.
 
#### Key Features
- **Simulated Execution**: Executes "paper" orders locally, tracking cash balances and positions without requiring real broker credentials.
- **Position Tracking**: Real-time tracking of average entry prices, realized PnL, and unrealized PnL.
- **Decision Integration**: Directly wires into `DecisionRecord` outputs, allowing the system to "live trade" in simulation mode.
- **Order History**: Stores all orders and PnL snapshots in Postgres for performance analysis.
 
#### CLI Usage
```bash
# Check current portfolio, positions, and equity
python -m backend.execution.cli execution-status

# Manually apply a trade from a specific decision ID
python -m backend.execution.cli execution-apply-decision --decision-id 123
```
 
#### API Endpoints
- `POST /execution/decision/{decision_id}`: Executes a trade for the given decision.
- `GET /execution/account`: Returns a complete snapshot of the trading account and positions.
- `GET /execution/orders`: Lists recent order history.
 
#### Implementation Note
This engine is designed as a layer over a pluggable "Broker Interface." Future updates will allow toggling `EXECUTION_MODE` to `live` to route these same decisions to Zerodha or Binance.
### 16. Instrument Catalog & Symbol Resolution (v1)

The Instrument module manages the master data for trading instruments, primarily focusing on Upstox. It provides a reliable way to sync instrument definitions and resolve human-friendly symbols (like `NIFTY`) to broker-specific keys.

#### Key Features
- **Upstox Sync**: Fetches and parses the full Upstox instrument master JSON, filtering for relevant segments (e.g., `NSE_INDEX`, `BSE_INDEX`).
- **Symbol Resolution**: Translates aliases like `NIFTY` or `SENSEX` into their respective `instrument_key` for use in data ingestion and execution.
- **Persistence**: Stores instrument metadata including tick size, lot size, expiry, and strike price in Postgres.

#### CLI Usage
- **Sync Instruments**:
  ```bash
  python -m backend.instruments.cli sync-upstox-instruments --segments NSE_INDEX,BSE_INDEX
  ```
- **List Instruments**:
  ```bash
  python -m backend.instruments.cli list-instruments --segment NSE_INDEX --limit 5
  ```
- **Resolve Symbol**:
  ```bash
  python -m backend.instruments.cli resolve-symbol --symbol NIFTY
  ```

#### API Endpoints
- `POST /instruments/sync`: Triggers a sync from Upstox.
- `GET /instruments`: Lists stored instruments with optional filters.
- `GET /instruments/resolve`: Resolves a symbol string to an instrument record.

### 17. Upstox Historical Candle Ingestion (v1)

This module enables historical market data backfill from Upstox Historical Candle Data V3. It integrates with the Instrument Catalog for symbol resolution and stores data in the unified `ohlc_bars` table.

#### Key Features
- **V3 API Support**: Uses Upstox's latest historical candle endpoint.
- **Symbol Mapping**: Automatically resolves symbols like `NIFTY` to internal Upstox keys via `instrument_master`.
- **Interval Normalization**: Maps standard intervals (`1m`, `5m`, `1h`, `1d`) to broker-specific formats.

#### Workflow
1. **Sync Instruments** (Must be done at least once):
   ```bash
   python -m backend.instruments.cli sync-upstox-instruments --segments NSE_INDEX,BSE_INDEX
   ```
2. **Backfill Candles**:
   ```bash
   python -m backend.ingestion.cli backfill --source upstox --symbol NIFTY --start 2024-05-01 --end 2024-05-15 --interval 5m
   ```
### 18. Dynamic Training Universe (v1)

The Orchestration module supports dynamic training universe selection, allowing the system to derive the list of symbols to train from either explicit configuration or the synced instrument catalog.

#### Key Features
- **Selection Modes**:
  - `explicit`: Uses `TRAIN_SYMBOLS` or `UPSTOX_DEFAULT_SYMBOLS`.
  - `catalog_filter`: Queries `instrument_master` based on segments and instrument types.
- **Symbol Normalization**: Automatically maps broker-specific names (e.g., `NIFTY 50`) to internal repo symbols (`NIFTY`).
- **Orchestration Wiring**: Prefect flows automatically use the dynamic universe if no explicit symbols are provided.

#### Configuration
Set the following in your `.env`:
- `TRAIN_UNIVERSE_MODE`: `explicit` or `catalog_filter`.
- `TRAIN_MAX_SYMBOLS`: Maximum symbols to select in catalog mode.
- `UPSTOX_UNIVERSE_INSTRUMENT_TYPES`: Comma-separated types (e.g., `INDEX`).

#### CLI Usage
- **Show Current Universe**:
  ```bash
  python -m backend.orchestration.cli show-universe --mode explicit
  python -m backend.orchestration.cli show-universe --mode catalog_filter
  ```
- **Run Training with Dynamic Universe**:
  ```bash
  # Automatically selects symbols based on TRAIN_UNIVERSE_MODE
  python -m backend.orchestration.cli train-price-models
  ```

#### API Endpoints
- `GET /orchestration/universe`: Returns the currently selected symbols and mode.

### 19. Training Data Preparation (v1)

The Orchestration module includes a dedicated pipeline to prepare historical data (OHLC and features) for the selected training universe. This ensures that models are always trained on the most recent data snapshots.

#### Key Features
- **Automated Workflow**: Combines instrument sync, universe selection, OHLC backfill, and feature calculation into a single call.
- **Fail-Safe Loop**: If one symbol fails to backfill, the pipeline continues with the remaining symbols and reports the errors in the summary.
- **Dynamic Window**: Supports configurable lookback periods (default 30 days).

#### CLI Usage
- **Run Data Preparation**:
  ```bash
  python -m backend.orchestration.cli prepare-training-data --mode catalog_filter --lookback-days 30
  ```
- **Run Daily Orchestration (Prep + Train)**:
  ```bash
  python -m backend.orchestration.cli run-daily
  ```

- `POST /orchestration/prepare-training-data`: Triggers the data preparation pipeline and returns a detailed summary of synced instruments and backfill statuses.

### 20. Trainability Checks (v1)

The system distinguishes between the **selected universe** (symbols chosen for training) and the **trainable universe** (symbols that have sufficient data for training). This prevents training failures due to missing or insufficient historical data.

#### Key Features
- **Deterministic Thresholds**: Minimum data requirements are automatically calculated from model architecture settings (input window + prediction horizon).
- **Safe Skipping**: The daily orchestrated flow automatically filters out non-trainable symbols before starting the model training phase.
- **Detailed Inspection**: CLI and API tools provide transparency into why specific symbols are skipped (e.g., `insufficient_ohlc` or `insufficient_features`).

#### CLI Usage
- **Inspect Trainability**:
  ```bash
  python -m backend.orchestration.cli show-trainability --mode catalog_filter --interval 5m
  ```
- **Review Preparation with Trainability**:
  ```bash
  python -m backend.orchestration.cli prepare-training-data --mode catalog_filter
  ```

- `GET /orchestration/trainability`: Returns a detailed breakdown of which symbols are ready for training and the underlying data counts for each.

### 21. Structured Training Execution (v1)

The orchestration layer provides a structured reporting mechanism for training runs. Instead of simple pass/fail logs, every training execution produces a machine-readable summary of the entire universe's status.

#### Key Features
- **Unified Summary**: Reports total, success, and failure counts for both Price Models and RL Agents in a single object.
- **Per-Symbol Details**: Captures the exact artifact path (e.g., `.pt` or `.zip` file) for every successful run and detailed error messages for failed ones.
- **Trainable Filtering**: The `train-trainable` workflow combines data preparation and training into a single optimized pipeline.

#### CLI Usage
- **Run Training for Ready Symbols**:
  ```bash
  python -m backend.orchestration.cli train-trainable --mode catalog_filter --lookback-days 30
  ```
- **Execute Daily Flow with Summary**:
  ```bash
  python -m backend.orchestration.cli run-daily
  ```

#### API Endpoints
- `POST /orchestration/train-trainable`: Triggers a full "Prep -> Filter -> Train" pipeline and returns the complete structured execution report.
- `POST /orchestration/run-daily`: Now returns the same enhanced structured result format as the CLI.

### 22. Model Registry (v1)

The system includes a lightweight Model Registry to track successful training runs and resolve the current active model for each symbol and interval.

#### Key Features
- **Automatic Registration**: Successful training runs are automatically recorded in the `trained_model_records` table.
- **Latest Model Resolution**: The registry automatically deactivates older models when a new successful model is registered for the same `(symbol, interval, model_type)`.
- **Inference Integration**: Inference services (Price Model and RL) query the registry to resolve the latest active model path, with a fallback to standard naming conventions.

#### CLI Usage
- **List All Registered Models**:
  ```bash
  python -m backend.orchestration.cli list-models --symbol NIFTY --active-only
  ```
- **Show Latest Active Model Details**:
  ```bash
  python -m backend.orchestration.cli show-latest-model --symbol NIFTY --interval 5m --model-type price_model
  ```

#### API Endpoints
- `GET /orchestration/models`: Returns a filtered list of registered model metadata.
- `GET /orchestration/models/latest`: Returns the metadata for the single latest active model for a given tuple.

### 23. Universe Inference Orchestration (v1)

The system can orchestrate inference across the entire selected universe in a single flow, ensuring that only "inference-ready" symbols are processed.

#### Readiness Criteria
A symbol is considered **inference-ready** if:
1. It has an **active Price Model** in the registry.
2. It has an **active RL Agent** in the registry.
3. It has **sufficient feature history** (e.g., last 60 minutes of joined OHLC and features) to support the models.

#### CLI Usage
- **Inspect Inference Readiness**:
  ```bash
  python -m backend.orchestration.cli show-inference-readiness --mode catalog_filter --interval 5m
  ```
- **Run Orchestrated Universe Inference**:
  ```bash
  python -m backend.orchestration.cli run-universe-inference --mode catalog_filter --interval 5m
  ```

#### API Endpoints
- `GET /orchestration/inference-readiness`: Returns readiness details for all symbols in the universe.
- `POST /orchestration/run-inference`: Triggers price prediction, RL action generation, and decision engine computation for all ready symbols.

### 24. Universe Paper Execution Orchestration (v1)

The system can orchestrate paper execution across the selected universe using the **latest available decisions**. It ensures that execution only happens for symbols that have actionable results.

#### Readiness Criteria
A symbol is considered **execution-ready** if:
1. It has a **latest stored DecisionRecord**.
2. Its `rl_action` is actionable (default: `BUY` or `SELL`). `HOLD` decisions are skipped by default.

#### CLI Usage
- **Inspect Execution Readiness**:
  ```bash
  python -m backend.orchestration.cli show-execution-readiness --mode catalog_filter --interval 5m
  ```
- **Run Orchestrated Universe Execution**:
  ```bash
  python -m backend.orchestration.cli run-universe-execution --mode catalog_filter --interval 5m
  ```

#### API Endpoints
- `GET /orchestration/execution-readiness`: Returns execution readiness details for all symbols in the universe.
- `POST /orchestration/run-execution`: Triggers paper execution for all symbols with actionable latest decisions.

### 25. End-to-End Operational Cycle Orchestration (v1)

The system can run a single unified **operational cycle** that wires inference and execution together for the current dynamic universe.

#### Cycle Workflow
1. **Resolve Universe**: Identifies symbols in the current training universe.
2. **Inference Readiness**: Filters for symbols with active models and sufficient feature history.
3. **Run Inference**: Generates price predictions, RL actions, and final decisions.
4. **Execution Readiness**: Filters for symbols with actionable latest decisions (e.g., BUY/SELL).
5. **Run Execution**: Executes trades through the paper trading engine.
6. **Reporting**: Returns a combined, machine-readable report of the entire cycle.

#### CLI Usage
```bash
python -m backend.orchestration.cli run-operational-cycle --mode catalog_filter --interval 5m
```
- Use `--allow-hold` to process `HOLD` decisions as ready for execution (default is actionable only).

#### API Endpoints
- `POST /orchestration/run-cycle`: Triggers the full end-to-end operational loop.

### 26. Orchestration Run History (v1)

The system maintains a lightweight history of all top-level orchestration runs. This allows operators to audit what happened during training, inference, execution, and full operational cycles.

#### Features
- **Compact Summaries**: Persists normalized counts and success/failure metadata.
- **Run Tracking**: Each orchestration result includes a `run_record_id` for traceability.
- **Unified Reporting**: Query recent runs across all orchestration types via CLI or API.

#### CLI Usage
- **List Recent Runs**:
  ```bash
  python -m backend.orchestration.cli list-runs --run-type cycle --limit 20
  ```
- **Show Specific Run Details**:
  ```bash
  python -m backend.orchestration.cli show-run --run-id 123
  ```

#### API Endpoints
- `GET /orchestration/runs`: Returns a list of recent orchestration records.
- `GET /orchestration/runs/{run_id}`: Returns full metadata and the parsed summary for a specific run.

### 27. Operational State Snapshot (v1)

The system provides a compact "latest status snapshot" that aggregates the current state of the dynamic universe, including readiness, model availability, latest decisions, and recent execution activity. This is designed for dashboard consumption and quick operator health checks.

#### CLI Usage
- **Show Current State**:
  ```bash
  python -m backend.orchestration.cli show-state --mode catalog_filter --interval 5m
  ```

#### API Endpoints
- `GET /orchestration/state`: Returns the latest operational snapshot. Optional `mode` and `interval` parameters are supported.

#### Key Snapshot Components
- **Universe**: Selected symbols and their inference/execution readiness.
- **Models**: Availability of active price models and RL agents.
- **Decisions**: Summary of latest actionable vs hold/missing decisions.
- **Execution State**: Lightweight indicator of orders and open positions.
- **Latest Runs**: Compact reference to the most recent orchestration run of each type.
 
### 28. Execution Guardrails (v1)

The system includes a lightweight safety layer to block or constrain automated paper execution. These guardrails are applied at the orchestration level, ensuring that execution only occurs when global safety conditions are met.

#### CLI Usage
```bash
# Inspect current guardrail evaluation for the universe
python -m backend.orchestration.cli show-execution-guardrails --mode catalog_filter --interval 5m

# Guardrails are automatically applied during execution
python -m backend.orchestration.cli run-universe-execution --mode catalog_filter --interval 5m
```

#### Key Features
- **Global Safety Switch**: Instantly enable or disable all execution via `EXECUTION_ENABLED`.
- **Action Filtering**: Restrict which RL actions (e.g., `BUY`, `SELL`) are permitted via `EXECUTION_ALLOWED_ACTIONS`.
- **Volume Capping**: Limit the number of symbols executed in a single run via `EXECUTION_MAX_SYMBOLS_PER_RUN`.
- **Traceability**: Blocked symbols and reasons (e.g., `max_symbols_cap`, `disallowed_action`) are recorded in run history and API responses.

#### API Endpoints
- `GET /orchestration/execution-guardrails`: Inspect current guardrail evaluation without side effects.
- `POST /orchestration/run-execution`: Now includes guardrail details in the result payload.

### 29. Manual Execution Overrides (v1)

Operators can manually override the latest execution intent for a symbol. Overrides are applied after guardrails and before actual paper execution.

#### CLI Usage
```bash
# Set a manual override (BUY, SELL, HOLD, SKIP)
python -m backend.orchestration.cli set-execution-override --symbol NIFTY --interval 5m --action SKIP --reason "Manual pause"

# List active overrides
python -m backend.orchestration.cli list-execution-overrides --interval 5m

# Clear an active override
python -m backend.orchestration.cli clear-execution-override --symbol NIFTY --interval 5m
```

#### Key Features
- **Operator Control**: Force-skip, force-buy, or force-sell specific symbols.
- **Non-Destructive**: Does not modify model inference or stored decisions.
- **Traceability**: Overrides include reasons/notes and are recorded in run history and state snapshots.
- **Last-Mile Safety**: Overrides act as the final decision layer before order submission.

#### API Endpoints
- `POST /orchestration/execution-overrides`: Create or update an override.
- `DELETE /orchestration/execution-overrides`: Clear an active override.
- `GET /orchestration/execution-overrides`: List active overrides.

### 30. Execution Idempotency + Duplicate Prevention (v1)

The system includes an idempotency layer to prevent redundant paper execution dispatches. This ensures that a specific automated decision or manual override is only dispatched once per operational source.

#### CLI Usage
```bash
# List recent execution dispatches
python -m backend.orchestration.cli list-execution-dispatches --symbol NIFTY --interval 5m

# Duplicate skips are automatically reported in execution runs
python -m backend.orchestration.cli run-universe-execution --mode catalog_filter --interval 5m
```

#### Key Features
- **Source Tracking**: Tracks dispatches using `(source_type, source_id)` identity.
- **Strict Prevention**: Once a decision ID or override ID is successfully dispatched, subsequent attempts are automatically skipped.
- **Operational Visibility**: Duplicate skips are flagged in run history, state snapshots, and the dashboard API.
- **Idempotency Status**: The `execution_dispatch` summary in state snapshots provides real-time visibility into which symbols have already been processed.

#### API Endpoints
- `GET /orchestration/execution-dispatches`: Lists historical dispatch records.
- `GET /orchestration/state`: Now includes a `execution_dispatch` block.
