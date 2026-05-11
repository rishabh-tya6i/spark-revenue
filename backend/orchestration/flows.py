import logging
from typing import List, Optional, Callable, Dict
from prefect import flow, task
from .utils import get_train_symbols, get_train_interval
from .data_prep import prepare_training_data_core
from .training_report import (
    run_price_training_for_symbols, 
    run_rl_training_for_symbols, 
    summarize_training_results,
    persist_training_results
)
from ..price_model.train import train_price_model
from ..rl.train import train_rl_agent
from .universe import get_training_universe
from .inference_readiness import get_inference_ready_symbols
from .inference_runner import (
    run_price_inference_for_symbols,
    run_rl_inference_for_symbols,
    compute_decisions_for_symbols,
    summarize_inference_results,
    run_inference_universe_core
)
from .execution_readiness import get_execution_ready_symbols
from .execution_runner import (
    execute_latest_decisions_for_symbols,
    summarize_execution_results,
    run_universe_execution_core
)
from .cycle_runner import run_operational_cycle_core
from ..db import SessionLocal

logger = logging.getLogger(__name__)

# --- Tasks ---

@task(name="Prepare Training Data Task")
def prepare_training_data_task(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    lookback_days: Optional[int] = None,
    sync_first: bool = True
):
    """
    Task to prepare OHLC and features for the training universe.
    """
    logger.info("Starting training data preparation task")
    return prepare_training_data_core(
        mode=mode, 
        interval=interval, 
        lookback_days=lookback_days, 
        sync_first=sync_first
    )

@task(name="Train Price Model Task")
def train_price_model_task(symbol: str, interval: str, epochs: int = 10):
    # This task is now primarily used by the flow-wrapped core.
    # The reporting logic is moved to run_price_training_for_symbols.
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

# --- Core Logic (Plain Python for testability) ---

def run_price_models_training_core(
    symbols: Optional[List[str]] = None, 
    interval: Optional[str] = None, 
    epochs: int = 10,
    runner: Callable = None  # Ignored in favor of structured reporter
):
    """
    Core logic for price model training. Returns structured results.
    """
    train_symbols = symbols or get_train_symbols()
    train_interval = interval or get_train_interval()
    
    logger.info(f"Starting Price Model training core for symbols: {train_symbols}")
    return run_price_training_for_symbols(train_symbols, train_interval, epochs=epochs)

def run_rl_agents_training_core(
    symbols: Optional[List[str]] = None, 
    interval: Optional[str] = None, 
    episodes: Optional[int] = None,
    runner: Callable = None  # Ignored in favor of structured reporter
):
    """
    Core logic for RL agent training. Returns structured results.
    """
    train_symbols = symbols or get_train_symbols()
    train_interval = interval or get_train_interval()
    
    logger.info(f"Starting RL Agent training core for symbols: {train_symbols}")
    return run_rl_training_for_symbols(train_symbols, train_interval, episodes=episodes)

def run_daily_training_flow_core(
    prep_runner: Callable,
    price_train_runner: Callable,
    rl_train_runner: Callable,
    mode: Optional[str] = None,
    interval: Optional[str] = None
):
    """
    Core logic for the daily master training flow.
    Returns structured results for both preparation and training.
    """
    logger.info("Starting Daily Training Master core logic")
    
    # 1. Prepare data
    prep_summary = prep_runner()
    
    # 2. Filter for trainable symbols
    trainable_symbols = prep_summary.get("trainable_symbols", [])
    
    if not trainable_symbols:
        logger.warning("No trainable symbols found after preparation. Skipping training.")
        result = {
            "status": "skipped", 
            "reason": "no_trainable_symbols",
            "data_prep": prep_summary,
            "trainable_symbols": [],
            "price_model_results": [],
            "rl_agent_results": [],
            "training_summary": summarize_training_results([], [])
        }
        
        # Persist run history
        from .run_history import register_orchestration_run
        from ..db import SessionLocal
        with SessionLocal() as session:
            run_record = register_orchestration_run(
                session=session,
                run_type="train",
                mode=mode,
                interval=interval,
                result=result
            )
            result["run_record_id"] = run_record["id"]
            
        return result

    # 3. Execute training pipelines
    price_results = price_train_runner(symbols=trainable_symbols)
    rl_results = rl_train_runner(symbols=trainable_symbols)
    
    # 4. Persist results to the Model Registry
    from ..db import SessionLocal
    with SessionLocal() as session:
        enriched_price = persist_training_results(session, price_results)
        enriched_rl = persist_training_results(session, rl_results)
    
    result = {
        "status": "completed",
        "data_prep": prep_summary,
        "trainable_symbols": trainable_symbols,
        "price_model_results": enriched_price,
        "rl_agent_results": enriched_rl,
        "training_summary": summarize_training_results(price_results, rl_results)
    }
    
    # 5. Persist run history
    from .run_history import register_orchestration_run
    with SessionLocal() as session:
        run_record = register_orchestration_run(
            session=session,
            run_type="train",
            mode=mode, 
            interval=interval,
            result=result
        )
        result["run_record_id"] = run_record["id"]
        
    return result

def run_train_trainable_core(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    lookback_days: Optional[int] = None,
    sync_first: bool = True,
    epochs: int = 10,
    episodes: Optional[int] = None,
) -> dict:
    """
    Top-level orchestration core that prepares data and then trains only trainable symbols.
    Reuses run_daily_training_flow_core but with flexible parameters.
    """
    return run_daily_training_flow_core(
        prep_runner=lambda: prepare_training_data_core(
            mode=mode, 
            interval=interval, 
            lookback_days=lookback_days, 
            sync_first=sync_first
        ),
        price_train_runner=lambda symbols: run_price_models_training_core(
            symbols=symbols, 
            interval=interval, 
            epochs=epochs
        ),
        rl_train_runner=lambda symbols: run_rl_agents_training_core(
            symbols=symbols, 
            interval=interval, 
            episodes=episodes
        ),
        mode=mode,
        interval=interval
    )

# --- Flows ---

@flow(name="Run Operational Cycle Flow")
def run_operational_cycle_flow(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    require_actionable: bool = True
):
    """
    Flow wrapper for the full end-to-end operational cycle.
    """
    return run_operational_cycle_core(
        mode=mode, 
        interval=interval, 
        require_actionable=require_actionable
    )

@flow(name="Run Universe Execution Flow")
def run_universe_execution_flow(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    require_actionable: bool = True
):
    """
    Flow wrapper around the universe execution core.
    """
    return run_universe_execution_core(
        mode=mode, 
        interval=interval, 
        require_actionable=require_actionable
    )

@flow(name="Run Universe Inference Flow")
def run_universe_inference_flow(
    mode: Optional[str] = None,
    interval: Optional[str] = None
):
    """
    Flow wrapper around the universe inference core.
    """
    return run_inference_universe_core(mode=mode, interval=interval)

@flow(name="Prepare Training Data Flow")
def prepare_training_data_flow(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    lookback_days: Optional[int] = None,
    sync_first: bool = True
):
    """
    Flow to prepare data (instruments, OHLC, features) for the training universe.
    """
    return prepare_training_data_task(
        mode=mode, 
        interval=interval, 
        lookback_days=lookback_days, 
        sync_first=sync_first
    )

@flow(name="Train Price Models Flow")
def train_price_models_flow(symbols: Optional[List[str]] = None, interval: Optional[str] = None, epochs: int = 10):
    """
    Flow to train price models for a set of symbols.
    """
    return run_price_models_training_core(symbols, interval, epochs)

@flow(name="Train RL Agents Flow")
def train_rl_agents_flow(symbols: Optional[List[str]] = None, interval: Optional[str] = None, episodes: Optional[int] = None):
    """
    Flow to train RL agents for a set of symbols.
    """
    return run_rl_agents_training_core(symbols, interval, episodes)

@flow(name="Daily Training Master Flow")
def daily_training_flow():
    """
    Master flow that prepares data and then runs all training pipelines for trainable symbols.
    """
    return run_daily_training_flow_core(
        prep_runner=prepare_training_data_flow,
        price_train_runner=train_price_models_flow,
        rl_train_runner=train_rl_agents_flow
    )

if __name__ == "__main__":
    daily_training_flow()
