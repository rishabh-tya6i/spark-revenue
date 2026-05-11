import argparse
import logging
import sys
import json
from .data_prep import prepare_training_data_core
from .trainability import get_trainable_symbols
from .inference_readiness import get_inference_ready_symbols
from .execution_readiness import get_execution_ready_symbols
from .flows import (
    train_price_models_flow, 
    train_rl_agents_flow, 
    daily_training_flow,
    prepare_training_data_flow,
    run_train_trainable_core,
    run_inference_universe_core,
    run_universe_execution_core,
    run_operational_cycle_core
)
from .universe import get_training_universe, parse_csv_setting
from .model_registry import list_models, get_latest_active_model, model_record_to_dict
from .run_history import (
    list_orchestration_runs, 
    get_orchestration_run, 
    orchestration_run_to_dict
)
from .state_snapshot import build_operational_state_snapshot
from .execution_guardrails import evaluate_execution_guardrails, parse_allowed_actions
from .execution_overrides import (
    set_execution_override, 
    clear_execution_override, 
    list_active_execution_overrides
)
from .execution_dispatch import list_dispatch_records, execution_dispatch_to_dict
from ..db import SessionLocal
from ..config import settings
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def print_training_summary(results: dict):
    """
    Prints a readable summary of the training run results.
    """
    print("\n--- Training Run Execution Report ---")
    print(f"Status: {results['status']}")
    if results.get("run_record_id"):
        print(f"Run Record ID: {results['run_record_id']}")
    
    if results['status'] == "skipped":
        print(f"Reason: {results.get('reason', 'Unknown')}")
        return

    summary = results.get("training_summary", {})
    price_sum = summary.get("price_model", {"success": 0, "total": 0})
    rl_sum = summary.get("rl_agent", {"success": 0, "total": 0})
    
    print(f"Price Models: {price_sum['success']}/{price_sum['total']} succeeded")
    print(f"RL Agents:    {rl_sum['success']}/{rl_sum['total']} succeeded")
    
    print("\nPrice Model Details:")
    for r in results.get("price_model_results", []):
        status = "OK" if r["status"] == "success" else f"FAILED - {r['error']}"
        print(f"  {r['symbol']}: {status}")
        if r.get("artifact_path"):
            print(f"    Artifact: {r['artifact_path']}")
            
    print("\nRL Agent Details:")
    for r in results.get("rl_agent_results", []):
        status = "OK" if r["status"] == "success" else f"FAILED - {r['error']}"
        print(f"  {r['symbol']}: {status}")
        if r.get("artifact_path"):
            print(f"    Artifact: {r['artifact_path']}")
    print("--------------------------------------")

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Spark Revenue Orchestration CLI")
    subparsers = parser.add_subparsers(dest="command", help="Orchestration commands")

    # show-universe
    universe_parser = subparsers.add_parser("show-universe", help="Inspect the current training universe")
    universe_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe selection mode")
    universe_parser.add_argument("--limit", type=int, help="Limit number of symbols in catalog mode")

    # show-trainability
    trainability_parser = subparsers.add_parser("show-trainability", help="Inspect which symbols are ready for training")
    trainability_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe selection mode")
    trainability_parser.add_argument("--interval", type=str, help="Override interval")

    # prepare-training-data
    prep_parser = subparsers.add_parser("prepare-training-data", help="Prepare OHLC and features for training")
    prep_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe selection mode")
    prep_parser.add_argument("--interval", type=str, help="Override data interval")
    prep_parser.add_argument("--lookback-days", type=int, help="Number of days to backfill")
    prep_parser.add_argument("--no-sync", action="store_true", help="Skip instrument sync first")

    # train-trainable
    tt_parser = subparsers.add_parser("train-trainable", help="Prepare data and train only ready symbols")
    tt_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    tt_parser.add_argument("--interval", type=str, help="Data interval")
    tt_parser.add_argument("--lookback-days", type=int, help="Backfill window")
    tt_parser.add_argument("--no-sync", action="store_true", help="Skip sync")
    tt_parser.add_argument("--epochs", type=int, default=10, help="Price model epochs")
    tt_parser.add_argument("--episodes", type=int, help="RL episodes")

    # list-models
    lm_parser = subparsers.add_parser("list-models", help="List registered models")
    lm_parser.add_argument("--symbol", type=str, help="Filter by symbol")
    lm_parser.add_argument("--interval", type=str, help="Filter by interval")
    lm_parser.add_argument("--model-type", type=str, help="Filter by model type")
    lm_parser.add_argument("--active-only", action="store_true", help="Show only active models")
    lm_parser.add_argument("--limit", type=int, default=50, help="Limit results")

    # show-latest-model
    sl_parser = subparsers.add_parser("show-latest-model", help="Show the latest active model for a symbol")
    sl_parser.add_argument("--symbol", type=str, required=True, help="Symbol")
    sl_parser.add_argument("--interval", type=str, required=True, help="Interval")
    sl_parser.add_argument("--model-type", type=str, required=True, help="Model type")

    # train-price-models
    price_parser = subparsers.add_parser("train-price-models", help="Train price prediction models (direct)")
    price_parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    price_parser.add_argument("--interval", type=str, help="Data interval")
    price_parser.add_argument("--epochs", type=int, default=10, help="Number of epochs")

    # train-rl-agents
    rl_parser = subparsers.add_parser("train-rl-agents", help="Train RL agents (direct)")
    rl_parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    rl_parser.add_argument("--interval", type=str, help="Data interval")
    rl_parser.add_argument("--episodes", type=int, help="Number of episodes")

    # run-daily
    subparsers.add_parser("run-daily", help="Run the daily master training flow")

    # show-inference-readiness
    inf_read_parser = subparsers.add_parser("show-inference-readiness", help="Inspect which symbols are ready for inference")
    inf_read_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe selection mode")
    inf_read_parser.add_argument("--interval", type=str, help="Override interval")

    # run-universe-inference
    run_inf_parser = subparsers.add_parser("run-universe-inference", help="Run orchestrated inference for the ready universe")
    run_inf_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    run_inf_parser.add_argument("--interval", type=str, help="Override interval")

    # run-universe-execution
    run_exec_parser = subparsers.add_parser("run-universe-execution", help="Run orchestrated paper execution for the ready universe")
    run_exec_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    run_exec_parser.add_argument("--interval", type=str, help="Override interval")
    run_exec_parser.add_argument("--allow-hold", action="store_true", help="Allow HOLD decisions to be processed as ready")

    # run-operational-cycle
    run_cycle_parser = subparsers.add_parser("run-operational-cycle", help="Run end-to-end operational cycle (Inf -> Dec -> Exec)")
    run_cycle_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    run_cycle_parser.add_argument("--interval", type=str, help="Override interval")
    run_cycle_parser.add_argument("--allow-hold", action="store_true", help="Allow HOLD decisions to be executed")
    
    # list-runs
    lr_parser = subparsers.add_parser("list-runs", help="List orchestration run history")
    lr_parser.add_argument("--run-type", type=str, choices=["train", "inference", "execution", "cycle"], help="Filter by run type")
    lr_parser.add_argument("--limit", type=int, default=50, help="Limit results")

    # show-run
    sr_parser = subparsers.add_parser("show-run", help="Show details for a specific orchestration run")
    sr_parser.add_argument("--run-id", type=int, required=True, help="Run ID")

    # show-state
    state_parser = subparsers.add_parser("show-state", help="Show the latest operational state snapshot")
    state_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    state_parser.add_argument("--interval", type=str, help="Override interval")

    # show-execution-readiness
    ser_parser = subparsers.add_parser("show-execution-readiness", help="Check symbols for execution readiness")
    ser_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    ser_parser.add_argument("--interval", type=str, help="Override interval")

    # show-execution-guardrails
    eg_parser = subparsers.add_parser("show-execution-guardrails", help="Evaluate execution guardrails for the universe")
    eg_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    eg_parser.add_argument("--interval", type=str, help="Override interval")

    # set-execution-override
    seo_parser = subparsers.add_parser("set-execution-override", help="Set a manual execution override for a symbol")
    seo_parser.add_argument("--symbol", type=str, required=True, help="Symbol")
    seo_parser.add_argument("--interval", type=str, required=True, help="Interval")
    seo_parser.add_argument("--action", type=str, choices=["BUY", "SELL", "HOLD", "SKIP"], required=True, help="Override action")
    seo_parser.add_argument("--reason", type=str, help="Optional reason for the override")

    # clear-execution-override
    ceo_parser = subparsers.add_parser("clear-execution-override", help="Clear an active execution override")
    ceo_parser.add_argument("--symbol", type=str, required=True, help="Symbol")
    ceo_parser.add_argument("--interval", type=str, required=True, help="Interval")

    # list-execution-overrides
    leo_parser = subparsers.add_parser("list-execution-overrides", help="List all currently active execution overrides")
    leo_parser.add_argument("--interval", type=str, help="Filter by interval")
    leo_parser.add_argument("--limit", type=int, default=100, help="Limit results")

    # list-execution-dispatches
    led_parser = subparsers.add_parser("list-execution-dispatches", help="List recent execution dispatches")
    led_parser.add_argument("--symbol", type=str, help="Filter by symbol")
    led_parser.add_argument("--interval", type=str, help="Filter by interval")
    led_parser.add_argument("--limit", type=int, default=100, help="Limit results")

    # show-execution-staleness
    ses_parser = subparsers.add_parser("show-execution-staleness", help="Inspect freshness of execution candidates")
    ses_parser.add_argument("--mode", type=str, choices=["explicit", "catalog_filter"], help="Universe mode")
    ses_parser.add_argument("--interval", type=str, help="Override interval")

    args = parser.parse_args()

    if args.command == "show-universe":
        mode = args.mode or settings.TRAIN_UNIVERSE_MODE
        print(f"--- Training Universe (Mode: {mode}) ---")
        
        with SessionLocal() as session:
            symbols = get_training_universe(session, mode=mode)
            
            if args.limit and mode == "catalog_filter":
                symbols = symbols[:args.limit]
            
            if not symbols:
                print("No symbols found in the selected universe.")
            else:
                for idx, sym in enumerate(symbols, 1):
                    print(f"{idx}. {sym}")
        print("-----------------------------------------")

    elif args.command == "show-trainability":
        mode = args.mode or settings.TRAIN_UNIVERSE_MODE
        interval = args.interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
        print(f"--- Trainability Inspection (Mode: {mode}, Interval: {interval}) ---")
        
        with SessionLocal() as db:
            symbols = get_training_universe(db, mode=mode)
            trainable_syms, details = get_trainable_symbols(db, symbols, interval)
            
            if not details:
                print("No symbols found in the universe.")
            else:
                print(f"{'SYMBOL':<15} {'OHLC':<10} {'FEAT':<10} {'TRAINABLE':<12} {'REASON'}")
                print("-" * 65)
                for d in details:
                    print(f"{d['symbol']:<15} {d['ohlc_count']:<10} {d['feature_count']:<10} {str(d['trainable']):<12} {d['reason'] or ''}")
        print("-----------------------------------------------------------------")

    elif args.command == "prepare-training-data":
        print("Starting data preparation...")
        summary = prepare_training_data_core(
            mode=args.mode,
            interval=args.interval,
            lookback_days=args.lookback_days,
            sync_first=not args.no_sync
        )
        print("\n--- Data Preparation Summary ---")
        print(f"Universe Mode: {summary['mode']}")
        print(f"Symbols: {', '.join(summary['symbols']) if summary['symbols'] else 'None'}")
        print(f"Interval: {summary['interval']}")
        print(f"Window: {summary['start']} to {summary['end']}")
        print(f"Instruments Synced: {summary['instrument_sync_count']}")
        
        print("\nOHLC Backfill Status:")
        for sym, status in summary["ohlc"].items():
            print(f"  {sym}: {status}")
            
        print("\nFeature Backfill Status:")
        for sym, status in summary["features"].items():
            print(f"  {sym}: {status}")
            
        print("\nTrainability Evaluation:")
        for d in summary["trainability"]:
            status_str = "READY" if d["trainable"] else f"SKIPPED ({d['reason']})"
            print(f"  {d['symbol']}: {status_str} (OHLC: {d['ohlc_count']}, Feat: {d['feature_count']})")
            
        print(f"\nFinal Trainable Symbols: {', '.join(summary['trainable_symbols']) if summary['trainable_symbols'] else 'None'}")
        print("----------------------------------")

    elif args.command == "train-trainable":
        print("Executing Train-Trainable pipeline...")
        results = run_train_trainable_core(
            mode=args.mode,
            interval=args.interval,
            lookback_days=args.lookback_days,
            sync_first=not args.no_sync,
            epochs=args.epochs,
            episodes=args.episodes
        )
        print_training_summary(results)

    elif args.command == "list-models":
        with SessionLocal() as db:
            records = list_models(db, args.symbol, args.interval, args.model_type, args.active_only, args.limit)
            if not records:
                print("No models found matching criteria.")
            else:
                print(f"\n{'ID':<5} {'SYMBOL':<15} {'INT':<5} {'TYPE':<12} {'STATUS':<8} {'ACT':<5} {'CREATED'}")
                print("-" * 80)
                for r in records:
                    active = "Y" if r.is_active else "N"
                    created = r.created_ts.strftime("%Y-%m-%d %H:%M") if r.created_ts else "N/A"
                    print(f"{r.id:<5} {r.symbol:<15} {r.interval:<5} {r.model_type:<12} {r.status:<8} {active:<5} {created}")
        print("-" * 80)

    elif args.command == "show-latest-model":
        with SessionLocal() as db:
            record = get_latest_active_model(db, args.symbol, args.interval, args.model_type)
            if not record:
                print("No active model found for given parameters.")
            else:
                print(f"\n--- Latest Active Model Record ---")
                data = model_record_to_dict(record)
                for k, v in data.items():
                    print(f"{k.upper():<20}: {v}")
                print("-----------------------------------")

    elif args.command == "train-price-models":
        symbols = parse_csv_setting(args.symbols) if args.symbols else None
        if not symbols:
            logger.info("No explicit symbols provided. Using dynamic training universe.")
        results = train_price_models_flow(symbols=symbols, interval=args.interval, epochs=args.epochs)
        # Wrap results if it's a single list (legacy) or already structured
        # For direct CLI, we just print a simple outcome
        print(f"Direct price training triggered for: {symbols or 'Universe'}")
        print(f"Results: {results}")

    elif args.command == "train-rl-agents":
        symbols = parse_csv_setting(args.symbols) if args.symbols else None
        if not symbols:
            logger.info("No explicit symbols provided. Using dynamic training universe.")
        results = train_rl_agents_flow(symbols=symbols, interval=args.interval, episodes=args.episodes)
        print(f"Direct RL training triggered for: {symbols or 'Universe'}")
        print(f"Results: {results}")

    elif args.command == "run-daily":
        print("Running daily training orchestration (Data Prep -> Model Training)...")
        results = daily_training_flow()
        print_training_summary(results)

    elif args.command == "show-inference-readiness":
        mode = args.mode or settings.TRAIN_UNIVERSE_MODE
        interval = args.interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
        print(f"--- Inference Readiness Inspection (Mode: {mode}, Interval: {interval}) ---")
        
        with SessionLocal() as db:
            symbols = get_training_universe(db, mode=mode)
            ready_syms, details = get_inference_ready_symbols(db, symbols, interval)
            
            if not details:
                print("No symbols found in the universe.")
            else:
                print(f"{'SYMBOL':<15} {'PRICE_M':<8} {'RL_A':<8} {'FEAT':<8} {'READY':<8} {'REASON'}")
                print("-" * 70)
                for d in details:
                    p_ready = "Y" if d["price_model_ready"] else "N"
                    r_ready = "Y" if d["rl_model_ready"] else "N"
                    f_ready = "Y" if d["feature_ready"] else "N"
                    ready = "Y" if d["ready"] else "N"
                    print(f"{d['symbol']:<15} {p_ready:<8} {r_ready:<8} {f_ready:<8} {ready:<8} {d['reason'] or ''}")
        print("----------------------------------------------------------------------")

    elif args.command == "run-universe-inference":
        print("Executing Universe Inference orchestration...")
        results = run_inference_universe_core(
            mode=args.mode,
            interval=args.interval
        )
        
        print("\n--- Universe Inference Execution Report ---")
        print(f"Status: {results['status']}")
        if results.get("run_record_id"):
            print(f"Run Record ID: {results['run_record_id']}")
            
        if results['status'] == "skipped":
            print(f"Reason: {results['reason']}")
            return

        print(f"Symbols Selected: {len(results['symbols'])}")
        print(f"Symbols Ready:    {len(results['inference_ready_symbols'])}")
        
        summary = results["summary"]
        print("\nSummary Counts:")
        print(f"  Price Prediction: {summary['price_prediction']['success']}/{summary['price_prediction']['total']}")
        print(f"  RL Action:        {summary['rl_action']['success']}/{summary['rl_action']['total']}")
        print(f"  Decision:         {summary['decision']['success']}/{summary['decision']['total']}")
        
        # Detailed errors
        for kind in ["price_results", "rl_results", "decision_results"]:
            fails = [r for r in results[kind] if r["status"] == "failed"]
            if fails:
                print(f"\nFailures in {kind}:")
                for f in fails:
                    print(f"  {f['symbol']}: {f['error']}")
        print("------------------------------------------")

    elif args.command == "show-execution-readiness":
        mode = args.mode or settings.TRAIN_UNIVERSE_MODE
        interval = args.interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
        print(f"--- Execution Readiness Inspection (Mode: {mode}, Interval: {interval}) ---")
        
        with SessionLocal() as db:
            symbols = get_training_universe(db, mode=mode)
            ready_syms, details = get_execution_ready_symbols(db, symbols, interval)
            
            if not details:
                print("No symbols found in the universe.")
            else:
                print(f"{'SYMBOL':<15} {'DEC_ID':<8} {'LABEL':<10} {'SCORE':<8} {'RL_ACT':<8} {'OVR':<4} {'OVR_ACT':<8} {'D_STAL':<6} {'O_STAL':<6} {'READY':<6} {'REASON'}")
                print("-" * 115)
                for d in details:
                    dec_id = d["decision_id"] or "N/A"
                    label = d["decision_label"] or "N/A"
                    score = f"{d['decision_score']:.2f}" if d["decision_score"] is not None else "N/A"
                    act = d["rl_action"] or "N/A"
                    ovr_active = "Y" if d.get("override_active") else "N"
                    ovr_action = d.get("override_action") or "N/A"
                    d_stale = "Y" if d.get("decision_stale") else "N"
                    o_stale = "Y" if d.get("override_stale") else "N"
                    ready = "Y" if d["ready"] else "N"
                    print(f"{d['symbol']:<15} {dec_id:<8} {label:<10} {score:<8} {act:<8} {ovr_active:<4} {ovr_action:<8} {d_stale:<6} {o_stale:<6} {ready:<6} {d['reason'] or ''}")
        print("-" * 115)

    elif args.command == "run-universe-execution":
        print("Executing Universe Paper Execution orchestration...")
        results = run_universe_execution_core(
            mode=args.mode,
            interval=args.interval,
            require_actionable=not args.allow_hold
        )
        
        print("\n--- Universe Execution Report ---")
        print(f"Status: {results['status']}")
        if results.get("run_record_id"):
            print(f"Run Record ID: {results['run_record_id']}")
            
        if results['status'] == "skipped":
            print(f"Reason: {results['reason']}")
            if results.get("guardrails"):
                g = results["guardrails"]
                print(f"Execution Enabled: {g['execution_enabled']}")
                if g['blocked_symbols']:
                    print("\nBlocked Symbols:")
                    for b in g['blocked_symbols']:
                        print(f"  {b['symbol']}: {b['reason']}")
            return

        print(f"Symbols Selected: {len(results['symbols'])}")
        print(f"Symbols Ready:    {len(results['execution_ready_symbols'])}")
        
        if results.get("guardrails"):
            g = results["guardrails"]
            print(f"Execution Enabled: {g['execution_enabled']}")
            print(f"Allowed Actions:   {', '.join(g['allowed_actions'])}")
            print(f"Max Per Run:       {g['max_symbols_per_run']}")
            if g['blocked_symbols']:
                print("\nBlocked Symbols:")
                for b in g['blocked_symbols']:
                    print(f"  {b['symbol']}: {b['reason']}")

        if results.get("overrides"):
            ov = results["overrides"]
            active_ov = ov.get("active_symbols", [])
            if active_ov:
                print(f"\nExecution Overrides Applied: {len(ov.get('applied', []))}")
                for a in ov.get("applied", []):
                    print(f"  {a['symbol']}: {a['override_action']}")

        summary = results["summary"]
        print("\nSummary Counts:")
        print(f"  Total Attempts: {summary['total']}")
        print(f"  Success:        {summary['success']}")
        print(f"  Skipped:        {summary['skipped']}")
        print(f"  Failed:         {summary['failed']}")

        if results.get("dispatch_summary"):
            ds = results["dispatch_summary"]
            print(f"\nDispatch Summary:")
            print(f"  New Dispatches:  {ds['new_dispatches']}")
            print(f"  Duplicate Skips: {ds['duplicate_skips']}")
        
        if results.get("staleness_summary"):
            ss = results["staleness_summary"]
            print(f"\nStaleness Summary:")
            print(f"  Stale Decisions: {len(ss['stale_decision_symbols'])}")
            print(f"  Stale Overrides: {len(ss['stale_override_symbols'])}")
        
        if results["execution_results"]:
            print("\nExecution Details:")
            print(f"{'SYMBOL':<15} {'STATUS':<10} {'SIDE':<6} {'QTY':<6} {'PRICE':<10} {'ORDER_ID':<8} {'ERROR'}")
            print("-" * 80)
            for r in results["execution_results"]:
                side = r["side"] or "-"
                qty = r["quantity"] or "-"
                price = f"{r['price']:.2f}" if r["price"] is not None else "-"
                oid = r["order_id"] or "-"
                err = r["error"] or ""
                
                status = r["status"]
                if r.get("dispatch", {}).get("duplicate"):
                    status = "DUP_SKIP"

                print(f"{r['symbol']:<15} {status:<10} {side:<6} {qty:<6} {price:<10} {oid:<8} {err}")
        print("----------------------------------")

    elif args.command == "run-operational-cycle":
        print("Executing End-to-End Operational Cycle...")
        results = run_operational_cycle_core(
            mode=args.mode,
            interval=args.interval,
            require_actionable=not args.allow_hold
        )
        
        print("\n=== End-to-End Operational Cycle Report ===")
        print(f"Overall Status: {results['status']}")
        if results.get("run_record_id"):
            print(f"Run Record ID: {results['run_record_id']}")
            
        if results['status'] == "skipped":
            print(f"Reason: {results['reason']}")
            # Show sub-inference if possible
            inf = results.get("inference", {})
            if inf:
                print(f"Inference Status: {inf.get('status')}")
            return

        summary = results["summary"]
        print(f"\nOperational Summary:")
        print(f"  Selected Symbols:      {summary['selected_symbols']}")
        print(f"  Inference Ready:       {summary['inference_ready_symbols']}")
        print(f"  Decisions Generated:   {summary['decision_success']}")
        print(f"  Execution Ready:       {summary['execution_ready_symbols']}")
        print(f"  Execution Success:     {summary['execution_success']}")
        print(f"  Execution Skipped:     {summary['execution_skipped']}")
        print(f"  Execution Failed:      {summary['execution_failed']}")

        print("\n--- Sub-Inference Report ---")
        inf = results["inference"]
        print(f"Status: {inf['status']}")
        inf_sum = inf.get("summary", {})
        if inf_sum:
            print(f"Decisions: {inf_sum.get('decision', {}).get('success', 0)}/{inf_sum.get('decision', {}).get('total', 0)}")

        print("\n--- Sub-Execution Report ---")
        exe = results["execution"]
        print(f"Status: {exe['status']}")
        if exe.get("reason"):
            print(f"Reason: {exe['reason']}")
            
        if exe.get("guardrails"):
            g = exe["guardrails"]
            if g['blocked_symbols']:
                print(f"Blocked by Guardrails: {len(g['blocked_symbols'])} symbols")
                for b in g['blocked_symbols']:
                    print(f"  {b['symbol']}: {b['reason']}")

        if exe.get("overrides"):
            ov = exe["overrides"]
            active_ov = ov.get("active_symbols", [])
            if active_ov:
                print(f"Execution Overrides Applied: {len(ov.get('applied', []))} symbols")
                for a in ov.get("applied", []):
                    print(f"  {a['symbol']}: {a['override_action']}")

        exe_sum = exe.get("summary", {})
        if exe_sum:
            print(f"Trades: {exe_sum.get('success', 0)} success, {exe_sum.get('skipped', 0)} skipped, {exe_sum.get('failed', 0)} failed")
        
        if exe.get("dispatch_summary"):
            ds = exe["dispatch_summary"]
            print(f"Dispatches: {ds.get('new_dispatches', 0)} new, {ds.get('duplicate_skips', 0)} duplicate skips")
        
        # Detail any failures
        all_failed = []
        for r in inf.get("decision_results", []):
            if r["status"] == "failed":
                all_failed.append(f"Inference {r['symbol']}: {r['error']}")
        for r in exe.get("execution_results", []):
            if r["status"] == "failed":
                all_failed.append(f"Execution {r['symbol']}: {r['error']}")
        
        if all_failed:
            print("\nOperational Failures:")
            for f in all_failed:
                print(f"  {f}")
        
        print("===========================================")
        
    elif args.command == "list-runs":
        with SessionLocal() as db:
            records = list_orchestration_runs(db, run_type=args.run_type, limit=args.limit)
            if not records:
                print("No orchestration runs found.")
            else:
                print(f"\n{'ID':<5} {'TYPE':<10} {'STATUS':<10} {'MODE':<15} {'INT':<5} {'SEL':<4} {'RDY':<4} {'S/K/F':<10} {'CREATED'}")
                print("-" * 100)
                for r in records:
                    counts = f"{r.success_count}/{r.skipped_count}/{r.failed_count}"
                    created = r.created_ts.strftime("%Y-%m-%d %H:%M")
                    print(f"{r.id:<5} {r.run_type:<10} {r.status:<10} {str(r.mode):<15} {str(r.interval):<5} {r.selected_symbols_count:<4} {r.ready_symbols_count:<4} {counts:<10} {created}")
        print("-" * 100)

    elif args.command == "show-run":
        with SessionLocal() as db:
            record = get_orchestration_run(db, args.run_id)
            if not record:
                print(f"Run record {args.run_id} not found.")
            else:
                print(f"\n--- Orchestration Run Record: {record.id} ---")
                data = orchestration_run_to_dict(record)
                # Print basic metadata
                for k in ["id", "run_type", "status", "reason", "mode", "interval", "created_ts"]:
                    print(f"{k.upper():<25}: {data.get(k)}")
                
                print(f"{'SELECTED_COUNT':<25}: {data['selected_symbols_count']}")
                print(f"{'READY_COUNT':<25}: {data['ready_symbols_count']}")
                print(f"{'SUCCESS/SKIP/FAIL':<25}: {data['success_count']}/{data['skipped_count']}/{data['failed_count']}")
                
                print("\nSUMMARY PAYLOAD:")
                print(json.dumps(data["summary"], indent=2))
                print("------------------------------------------")

    elif args.command == "show-state":
        with SessionLocal() as db:
            snapshot = build_operational_state_snapshot(db, mode=args.mode, interval=args.interval)
            
            print(f"\n=== Operational State Snapshot (Mode: {snapshot['mode']}, Interval: {snapshot['interval']}) ===")
            
            print("\n[ Universe ]")
            print(f"Selected Symbols:      {', '.join(snapshot['symbols']) if snapshot['symbols'] else 'None'}")
            print(f"Inference Ready:       {', '.join(snapshot['inference_ready_symbols']) if snapshot['inference_ready_symbols'] else 'None'}")
            print(f"Execution Ready:       {', '.join(snapshot['execution_ready_symbols']) if snapshot['execution_ready_symbols'] else 'None'}")
            
            print("\n[ Models ]")
            m = snapshot['models']
            print(f"Symbols Checked:       {m['symbols_checked']}")
            print(f"Price Model OK:        {', '.join(m['price_model_available']) if m['price_model_available'] else 'None'}")
            print(f"RL Agent OK:           {', '.join(m['rl_agent_available']) if m['rl_agent_available'] else 'None'}")
            if m['missing_price_model']:
                print(f"Missing Price Model:   {', '.join(m['missing_price_model'])}")
            if m['missing_rl_agent']:
                print(f"Missing RL Agent:      {', '.join(m['missing_rl_agent'])}")
                
            print("\n[ Decisions ]")
            d = snapshot['decisions']
            print(f"Has Latest Decision:   {', '.join(d['has_decision']) if d['has_decision'] else 'None'}")
            print(f"Actionable (BUY/SELL): {', '.join(d['actionable']) if d['actionable'] else 'None'}")
            if d['hold']:
                print(f"Hold:                  {', '.join(d['hold'])}")
            if d['missing']:
                print(f"Missing Decisions:     {', '.join(d['missing'])}")
                
            print("\n[ Execution State ]")
            e = snapshot['execution_state']
            print(f"Has Orders:            {', '.join(e['has_orders']) if e['has_orders'] else 'None'}")
            print(f"Open Positions:        {', '.join(e['open_positions']) if e['open_positions'] else 'None'}")
            if e['no_activity']:
                print(f"No Activity:           {', '.join(e['no_activity'])}")
                
            print("\n[ Execution Overrides ]")
            ov = snapshot.get('execution_overrides', {})
            active_ov = ov.get('active_symbols', [])
            print(f"Active Overrides:      {', '.join(active_ov) if active_ov else 'None'}")
            if active_ov:
                for sym, action in ov.get('actions', {}).items():
                    print(f"  {sym}: {action}")

            print("\n[ Latest Runs ]")
            for rtype, rdata in snapshot['latest_runs'].items():
                if rdata:
                    created = rdata['created_ts'].split('T')[0] # Simple date
                    print(f"  {rtype.capitalize():<12}: ID {rdata['id']} - {rdata['status']} ({created})")
                else:
                    print(f"  {rtype.capitalize():<12}: None")
            
            print("=========================================================================")

    elif args.command == "show-execution-guardrails":
        mode = args.mode or settings.TRAIN_UNIVERSE_MODE
        interval = args.interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
        print(f"\n=== Execution Guardrail Inspection (Mode: {mode}, Interval: {interval}) ===")
        
        with SessionLocal() as db:
            symbols = get_training_universe(db, mode=mode)
            ready_syms, details = get_execution_ready_symbols(db, symbols, interval)
            
            guardrail_result = evaluate_execution_guardrails(details)
            
            print(f"Execution Enabled:     {guardrail_result['execution_enabled']}")
            print(f"Allowed Actions:       {', '.join(guardrail_result['allowed_actions'])}")
            print(f"Max Symbols Per Run:   {guardrail_result['max_symbols_per_run']}")
            
            print(f"\nReady Symbols:         {', '.join(guardrail_result['requested_ready_symbols']) if guardrail_result['requested_ready_symbols'] else 'None'}")
            print(f"Allowed Symbols:       {', '.join(guardrail_result['allowed_symbols']) if guardrail_result['allowed_symbols'] else 'None'}")
            
            if guardrail_result['blocked_symbols']:
                print("\nBlocked Symbols:")
                for b in guardrail_result['blocked_symbols']:
                    print(f"  {b['symbol']}: {b['reason']}")
            else:
                print("\nBlocked Symbols:       None")
        print("----------------------------------------------------------------------")

    elif args.command == "set-execution-override":
        with SessionLocal() as db:
            res = set_execution_override(db, args.symbol, args.interval, args.action, args.reason)
            print(f"\nOverride set successfully for {args.symbol} ({args.interval}): {args.action}")
            print(f"Reason: {args.reason or 'None'}")

    elif args.command == "clear-execution-override":
        with SessionLocal() as db:
            res = clear_execution_override(db, args.symbol, args.interval)
            if res:
                print(f"\nActive override cleared for {args.symbol} ({args.interval})")
            else:
                print(f"\nNo active override found for {args.symbol} ({args.interval})")

    elif args.command == "list-execution-overrides":
        with SessionLocal() as db:
            records = list_active_execution_overrides(db, args.interval, args.limit)
            if not records:
                print("\nNo active execution overrides found.")
            else:
                print(f"\n--- Active Execution Overrides ({len(records)}) ---")
                print(f"{'SYMBOL':<15} {'INT':<5} {'ACTION':<8} {'CREATED':<20} {'REASON'}")
                print("-" * 80)
                for r in records:
                    created = r.created_ts.strftime("%Y-%m-%d %H:%M")
                    print(f"{r.symbol:<15} {r.interval:<5} {r.override_action:<8} {created:<20} {r.reason or ''}")
                print("-" * 80)
    elif args.command == "list-execution-dispatches":
        with SessionLocal() as db:
            records = list_dispatch_records(db, args.symbol, args.interval, args.limit)
            if not records:
                print("\nNo execution dispatches found.")
            else:
                print(f"\n--- Execution Dispatches ({len(records)}) ---")
                print(f"{'ID':<4} {'SYMBOL':<15} {'INT':<5} {'TYPE':<10} {'SRC_ID':<8} {'ACT':<8} {'STATUS':<10} {'ORDER_ID':<8} {'CREATED'}")
                print("-" * 100)
                for r in records:
                    created = r.created_ts.strftime("%Y-%m-%d %H:%M")
                    print(f"{r.id:<4} {r.symbol:<15} {r.interval:<5} {r.source_type:<10} {r.source_id:<8} {r.dispatched_action:<8} {r.status:<10} {r.order_id or 'N/A':<8} {created}")
                print("-" * 100)
    elif args.command == "show-execution-staleness":
        mode = args.mode or settings.TRAIN_UNIVERSE_MODE
        interval = args.interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
        print(f"\n=== Execution Staleness Inspection (Mode: {mode}, Interval: {interval}) ===")
        
        with SessionLocal() as db:
            symbols = get_training_universe(db, mode=mode)
            _, details = get_execution_ready_symbols(db, symbols, interval)
            
            print(f"{'SYMBOL':<15} {'DECISION_TS':<20} {'OVERRIDE_TS':<20} {'D_STALE':<8} {'O_STALE':<8} {'REASON'}")
            print("-" * 100)
            for d in details:
                d_ts = d["decision_ts"].strftime("%Y-%m-%d %H:%M") if d["decision_ts"] else "N/A"
                o_ts = d["override_created_ts"].strftime("%Y-%m-%d %H:%M") if d["override_created_ts"] else "N/A"
                d_stale = "Y" if d["decision_stale"] else "N"
                o_stale = "Y" if d["override_stale"] else "N"
                
                reason = ""
                if d.get("override_active"):
                    if d["override_stale"]:
                        reason = "STALE_OVERRIDE"
                elif d["decision_stale"]:
                    reason = "STALE_DECISION"
                
                print(f"{d['symbol']:<15} {d_ts:<20} {o_ts:<20} {d_stale:<8} {o_stale:<8} {reason}")
        print("-" * 100)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
