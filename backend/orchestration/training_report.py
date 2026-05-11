import logging
from typing import List, Dict, Optional, Tuple
from ..price_model.train import train_price_model
from ..rl.train import train_rl_agent

logger = logging.getLogger(__name__)

def run_price_training_for_symbols(symbols: List[str], interval: str, epochs: int = 10) -> List[Dict]:
    """
    Runs price model training for a list of symbols and returns structured results.
    Each symbol is isolated: one failure does not stop the loop.
    """
    results = []
    for symbol in symbols:
        try:
            logger.info(f"Orchestrating price model training for {symbol}")
            artifact_path = train_price_model(symbol, interval, epochs=epochs)
            
            if artifact_path:
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "trainer": "price_model",
                    "status": "success",
                    "artifact_path": artifact_path,
                    "error": None,
                })
            else:
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "trainer": "price_model",
                    "status": "failed",
                    "artifact_path": None,
                    "error": "Training returned no artifact path (likely data missing or build failure)",
                })
        except Exception as e:
            logger.error(f"Price model training failed for {symbol}: {str(e)}")
            results.append({
                "symbol": symbol,
                "interval": interval,
                "trainer": "price_model",
                "status": "failed",
                "artifact_path": None,
                "error": str(e),
            })
    return results

def run_rl_training_for_symbols(symbols: List[str], interval: str, episodes: Optional[int] = None) -> List[Dict]:
    """
    Runs RL agent training for a list of symbols and returns structured results.
    Each symbol is isolated: one failure does not stop the loop.
    """
    results = []
    for symbol in symbols:
        try:
            logger.info(f"Orchestrating RL agent training for {symbol}")
            artifact_path = train_rl_agent(symbol, interval, episodes=episodes)
            
            if artifact_path:
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "trainer": "rl_agent",
                    "status": "success",
                    "artifact_path": artifact_path,
                    "error": None,
                })
            else:
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "trainer": "rl_agent",
                    "status": "failed",
                    "artifact_path": None,
                    "error": "Training returned no artifact path (likely data missing or build failure)",
                })
        except Exception as e:
            logger.error(f"RL agent training failed for {symbol}: {str(e)}")
            results.append({
                "symbol": symbol,
                "interval": interval,
                "trainer": "rl_agent",
                "status": "failed",
                "artifact_path": None,
                "error": str(e),
            })
    return results

def summarize_training_results(price_results: List[Dict], rl_results: List[Dict]) -> Dict:
    """
    Returns a compact summary of training outcomes (totals, success, failed).
    """
    price_total = len(price_results)
    price_success = sum(1 for r in price_results if r["status"] == "success")
    
    rl_total = len(rl_results)
    rl_success = sum(1 for r in rl_results if r["status"] == "success")
    
    return {
        "price_model": {
            "total": price_total,
            "success": price_success,
            "failed": price_total - price_success,
        },
        "rl_agent": {
            "total": rl_total,
            "success": rl_success,
            "failed": rl_total - rl_success,
        }
    }

def split_training_status(results: List[Dict]) -> Tuple[List[str], List[str]]:
    """
    Helper to separate succeeded vs failed symbol names.
    Returns (success_symbols, failed_symbols)
    """
    success = [r["symbol"] for r in results if r["status"] == "success"]
    failed = [r["symbol"] for r in results if r["status"] != "success"]
    return success, failed

def persist_training_results(session, results: List[Dict]) -> List[Dict]:
    """
    Persists training result dicts into the model registry.
    Enriches the results with registry metadata like record ID and active flag.
    """
    from .model_registry import register_trained_model
    
    enriched = []
    for r in results:
        # Map 'trainer' to 'model_type'
        model_type = r["trainer"]
        
        record = register_trained_model(
            session=session,
            symbol=r["symbol"],
            interval=r["interval"],
            model_type=model_type,
            artifact_path=r["artifact_path"],
            status=r["status"],
            notes=r.get("error")
        )
        
        # Enrich result dict with registry info
        r_enriched = r.copy()
        r_enriched["registry_record_id"] = record.id
        r_enriched["active"] = bool(record.is_active)
        enriched.append(r_enriched)
        
    return enriched
