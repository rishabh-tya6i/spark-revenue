import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from backend.orchestration.execution_runner import (
    execute_latest_decisions_for_symbols,
    summarize_execution_results
)

def test_summarize_execution_results():
    results = [
        {"status": "success", "dispatch": {"registered": True}},
        {"status": "skipped"}, # stale or something
        {"status": "failed", "dispatch": {"registered": True}}, # failed but recorded
        {"status": "success", "dispatch": {"registered": True}},
        {"status": "skipped", "dispatch": {"duplicate": True}}
    ]
    summary = summarize_execution_results(results)
    assert summary["total"] == 5
    assert summary["success"] == 2
    assert summary["skipped"] == 2
    assert summary["failed"] == 1
    assert summary["new_dispatches"] == 3
    assert summary["duplicate_skips"] == 1

def test_execute_latest_decisions_runner():
    with patch("backend.orchestration.execution_runner.SessionLocal") as mock_session_cls, \
         patch("backend.orchestration.execution_runner.ExecutionService") as mock_service_cls, \
         patch("backend.orchestration.execution_runner.get_active_execution_override") as mock_get_ov, \
         patch("backend.orchestration.execution_runner.has_been_dispatched", return_value=False):
        
        mock_get_ov.return_value = None
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_service = mock_service_cls.return_value
        mock_service.get_or_create_default_account.return_value = MagicMock(id=1)
        
        # 1. Missing decision
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "missing_decision"
        
        # 2. Success
        mock_decision = MagicMock(id=101, symbol="NIFTY", interval="5m", timestamp=datetime.utcnow())
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_decision
        
        mock_order = MagicMock(id=12, side="BUY", quantity=1.0, price=20000.0)
        mock_service.execute_decision.return_value = mock_order
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "success"
        assert res[0]["order_id"] == 12
        assert res[0]["price"] == 20000.0
        
        # 3. Skipped (HOLD / No trade)
        mock_service.execute_decision.return_value = None
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "no trade generated"
        
        # 4. Failed
        mock_service.execute_decision.side_effect = Exception("Execution engine error")
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "failed"
        assert "Execution engine error" in res[0]["error"]

def test_run_universe_execution_core_guardrails():
    from backend.orchestration.execution_runner import run_universe_execution_core
    
    with patch("backend.orchestration.execution_runner.get_training_universe") as mock_uni, \
         patch("backend.orchestration.execution_runner.get_execution_ready_symbols") as mock_ready, \
         patch("backend.orchestration.execution_runner.evaluate_execution_guardrails") as mock_guard, \
         patch("backend.orchestration.execution_runner.register_orchestration_run") as mock_reg, \
         patch("backend.orchestration.execution_runner.execute_latest_decisions_for_symbols") as mock_exec, \
         patch("backend.orchestration.execution_runner.get_active_execution_override") as mock_get_ov:
        
        mock_get_ov.return_value = None
        mock_uni.return_value = ["NIFTY", "SENSEX"]
        mock_ready.return_value = (["NIFTY", "SENSEX"], [
            {"symbol": "NIFTY", "ready": True, "rl_action": "BUY"},
            {"symbol": "SENSEX", "ready": True, "rl_action": "SELL"}
        ])
        
        # Block SENSEX by guardrail
        mock_guard.return_value = {
            "execution_enabled": True,
            "allowed_actions": ["BUY"],
            "max_symbols_per_run": 1,
            "requested_ready_symbols": ["NIFTY", "SENSEX"],
            "allowed_symbols": ["NIFTY"],
            "blocked_symbols": [{"symbol": "SENSEX", "reason": "disallowed_action"}]
        }
        mock_reg.return_value = {"id": 1}
        mock_exec.return_value = ([{"symbol": "NIFTY", "status": "success", "side": "BUY", "quantity": 1, "price": 100, "order_id": 1, "error": None}], {})
        
        result = run_universe_execution_core(mode="explicit", interval="5m")
        
        assert result["status"] == "completed"
        assert result["execution_ready_symbols"] == ["NIFTY", "SENSEX"]
        assert result["guardrails"]["allowed_symbols"] == ["NIFTY"]
        assert len(result["execution_results"]) == 1
        assert result["execution_results"][0]["symbol"] == "NIFTY"
        
        # Test fully blocked
        mock_guard.return_value["allowed_symbols"] = []
        mock_guard.return_value["blocked_symbols"].append({"symbol": "NIFTY", "reason": "disallowed_action"})
        
        result = run_universe_execution_core(mode="explicit", interval="5m")
        assert result["status"] == "skipped"
        assert result["reason"] == "blocked_by_guardrails"
        assert result["execution_results"] == []
        assert "dispatch_summary" in result
        assert result["dispatch_summary"]["new_dispatches"] == 0
        assert result["dispatch_summary"]["duplicate_skips"] == 0

def test_run_universe_execution_core_no_ready_symbols():
    from backend.orchestration.execution_runner import run_universe_execution_core
    
    with patch("backend.orchestration.execution_runner.get_training_universe") as mock_uni, \
         patch("backend.orchestration.execution_runner.get_execution_ready_symbols") as mock_ready, \
         patch("backend.orchestration.execution_runner.evaluate_execution_guardrails") as mock_guard, \
         patch("backend.orchestration.execution_runner.register_orchestration_run") as mock_reg:
        
        mock_uni.return_value = ["NIFTY"]
        # No ready symbols
        mock_ready.return_value = ([], [{"symbol": "NIFTY", "ready": False, "reason": "missing"}])
        mock_guard.return_value = {
            "execution_enabled": True, 
            "allowed_actions": ["BUY", "SELL"],
            "max_symbols_per_run": 5,
            "requested_ready_symbols": ["NIFTY"],
            "allowed_symbols": [], 
            "blocked_symbols": []
        }
        mock_reg.return_value = {"id": 1}
        
        result = run_universe_execution_core(mode="explicit", interval="5m")
        
        assert result["status"] == "skipped"
        assert result["reason"] == "no_execution_ready_symbols"
        assert "dispatch_summary" in result
        assert result["dispatch_summary"]["new_dispatches"] == 0
        assert result["dispatch_summary"]["duplicate_skips"] == 0

def test_execute_latest_decisions_with_overrides():
    with patch("backend.orchestration.execution_runner.SessionLocal") as mock_session_cls, \
         patch("backend.orchestration.execution_runner.ExecutionService") as mock_service_cls, \
         patch("backend.orchestration.execution_runner.get_active_execution_override") as mock_get_ov, \
         patch("backend.orchestration.execution_runner.has_been_dispatched", return_value=False):
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_service = mock_service_cls.return_value
        mock_service.get_or_create_default_account.return_value = MagicMock(id=1)
        
        # 1. SKIP Override
        mock_ov = MagicMock(symbol="NIFTY", override_action="SKIP", reason="Manual skip")
        mock_ov.id = 1
        mock_ov.interval = "5m"
        mock_ov.is_active = 1
        mock_ov.created_ts = datetime.utcnow()
        mock_ov.cleared_ts = None
        mock_get_ov.return_value = mock_ov
        
        res, ctx = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "manual_override_skip"
        assert ctx["active_symbols"] == ["NIFTY"]
        
        # 2. BUY Override
        mock_ov.override_action = "BUY"
        mock_order = MagicMock(id=55, side="BUY", quantity=1.0, price=100.0)
        mock_service.execute_manual_action.return_value = mock_order
        
        res, ctx = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "success"
        assert res[0]["order_id"] == 55
        assert res[0]["side"] == "BUY"
        
        # 3. HOLD Override
        mock_ov.override_action = "HOLD"
        res, ctx = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "manual_override_hold"

        # 4. No Override
        mock_get_ov.return_value = None
        mock_decision = MagicMock(id=101, timestamp=datetime.utcnow())
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_decision
        mock_service.execute_decision.return_value = mock_order
        
        res, ctx = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "success"
        assert res[0]["decision_id"] == 101
        assert ctx["active_symbols"] == []

def test_execute_latest_decisions_idempotency():
    with patch("backend.orchestration.execution_runner.SessionLocal") as mock_session_cls, \
         patch("backend.orchestration.execution_runner.ExecutionService") as mock_service_cls, \
         patch("backend.orchestration.execution_runner.get_active_execution_override") as mock_get_ov, \
         patch("backend.orchestration.execution_runner.has_been_dispatched") as mock_has_disp, \
         patch("backend.orchestration.execution_runner.register_dispatch_record") as mock_reg_disp:
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_service = mock_service_cls.return_value
        mock_service.get_or_create_default_account.return_value = MagicMock(id=1)
        
        # 1. Normal path - already dispatched
        mock_get_ov.return_value = None
        mock_decision = MagicMock(id=101, symbol="NIFTY", interval="5m", timestamp=datetime.utcnow())
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_decision
        
        mock_has_disp.return_value = True
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "already_dispatched"
        assert res[0]["dispatch"]["duplicate"] is True
        assert mock_service.execute_decision.called is False
        
        # 2. Override path - already dispatched
        mock_ov = MagicMock(id=500, symbol="NIFTY", override_action="BUY", created_ts=datetime.utcnow())
        mock_get_ov.return_value = mock_ov
        mock_has_disp.return_value = True # dispatch check for override
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "already_dispatched"
        assert mock_service.execute_manual_action.called is False

        # 3. Normal path - NOT dispatched (register called)
        mock_get_ov.return_value = None
        mock_has_disp.return_value = False
        mock_order = MagicMock(id=12, side="BUY", quantity=1.0, price=100.0)
        mock_service.execute_decision.return_value = mock_order
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "success"
        assert mock_reg_disp.called is True
        args, kwargs = mock_reg_disp.call_args
        # positional check: register_dispatch_record(session, symbol, interval, source_type, source_id, ...)
        assert args[3] == "decision"
        assert args[4] == 101
def test_execute_latest_decisions_staleness():
    with patch("backend.orchestration.execution_runner.SessionLocal") as mock_session_cls, \
         patch("backend.orchestration.execution_runner.ExecutionService") as mock_service_cls, \
         patch("backend.orchestration.execution_runner.get_active_execution_override") as mock_get_ov, \
         patch("backend.orchestration.execution_runner.has_been_dispatched", return_value=False), \
         patch("backend.orchestration.execution_runner.evaluate_execution_source_staleness") as mock_stale:
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_service = mock_service_cls.return_value
        mock_service.get_or_create_default_account.return_value = MagicMock(id=1)
        
        # 1. Stale Decision
        mock_get_ov.return_value = None
        mock_decision = MagicMock(id=101, symbol="NIFTY", timestamp=datetime.utcnow())
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_decision
        
        mock_stale.return_value = {
            "decision_stale": True,
            "override_stale": False,
            "decision_max_age_minutes": 30,
            "override_max_age_minutes": 60
        }
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "stale_decision"
        assert res[0]["staleness"]["decision_stale"] is True
        assert mock_service.execute_decision.called is False
        
        # 2. Stale Override
        mock_ov = MagicMock(id=500, symbol="NIFTY", override_action="BUY", created_ts=datetime.utcnow())
        mock_get_ov.return_value = mock_ov
        mock_stale.return_value["override_stale"] = True
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "skipped"
        assert res[0]["error"] == "stale_override"
        assert res[0]["staleness"]["override_stale"] is True
        assert mock_service.execute_manual_action.called is False
        
        # 3. Fresh Decision
        mock_get_ov.return_value = None
        mock_stale.return_value["decision_stale"] = False
        mock_order = MagicMock(id=12, side="BUY", quantity=1.0, price=100.0)
        mock_service.execute_decision.return_value = mock_order
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["status"] == "success"
        assert res[0]["error"] is None
        assert res[0]["staleness"]["decision_stale"] is False
def test_run_universe_execution_dispatch_accounting_with_staleness():
    from backend.orchestration.execution_runner import run_universe_execution_core
    
    with patch("backend.orchestration.execution_runner.get_training_universe") as mock_uni, \
         patch("backend.orchestration.execution_runner.get_execution_ready_symbols") as mock_ready, \
         patch("backend.orchestration.execution_runner.evaluate_execution_guardrails") as mock_guard, \
         patch("backend.orchestration.execution_runner.register_orchestration_run") as mock_reg, \
         patch("backend.orchestration.execution_runner.execute_latest_decisions_for_symbols") as mock_exec:
        
        mock_uni.return_value = ["NIFTY", "SENSEX"]
        mock_ready.return_value = (["NIFTY", "SENSEX"], [
            {"symbol": "NIFTY", "ready": True},
            {"symbol": "SENSEX", "ready": True}
        ])
        mock_guard.return_value = {
            "execution_enabled": True,
            "allowed_actions": ["BUY", "SELL"],
            "max_symbols_per_run": 5,
            "requested_ready_symbols": ["NIFTY", "SENSEX"],
            "allowed_symbols": ["NIFTY", "SENSEX"],
            "blocked_symbols": []
        }
        mock_reg.return_value = {"id": 1}
        
        # Scenario: NIFTY is stale, SENSEX is successful
        mock_exec.return_value = ([
            {
                "symbol": "NIFTY", 
                "status": "skipped", 
                "error": "stale_decision", 
                "dispatch": None # No dispatch for stale
            },
            {
                "symbol": "SENSEX", 
                "status": "success", 
                "dispatch": {"registered": True, "duplicate": False}
            }
        ], {})
        
        result = run_universe_execution_core(mode="explicit", interval="5m")
        
        assert result["status"] == "completed"
        assert result["dispatch_summary"]["new_dispatches"] == 1
        assert result["dispatch_summary"]["duplicate_skips"] == 0
        
        # Scenario: Override is stale
        mock_exec.return_value = ([
            {
                "symbol": "NIFTY", 
                "status": "skipped", 
                "error": "stale_override",
                "dispatch": None
            }
        ], {})
        mock_ready.return_value = (["NIFTY"], [{"symbol": "NIFTY", "ready": True}])
        mock_guard.return_value["allowed_symbols"] = ["NIFTY"]
        
        result = run_universe_execution_core(mode="explicit", interval="5m")
        assert result["dispatch_summary"]["new_dispatches"] == 0

def test_execute_latest_decisions_dispatch_metadata():
    with patch("backend.orchestration.execution_runner.SessionLocal") as mock_session_cls, \
         patch("backend.orchestration.execution_runner.ExecutionService") as mock_service_cls, \
         patch("backend.orchestration.execution_runner.get_active_execution_override") as mock_get_ov, \
         patch("backend.orchestration.execution_runner.has_been_dispatched", return_value=False):
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_service = mock_service_cls.return_value
        mock_service.get_or_create_default_account.return_value = MagicMock(id=1)
        mock_get_ov.return_value = None
        
        # 1. Success path
        mock_decision = MagicMock(id=101, symbol="NIFTY", interval="5m", timestamp=datetime.utcnow(), rl_action="BUY")
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_decision
        mock_service.execute_decision.return_value = MagicMock(id=1, side="BUY", quantity=1.0, price=100.0)
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["dispatch"]["registered"] is True
        assert res[0]["dispatch"]["duplicate"] is False
        
        # 2. Manual skip path
        mock_ov = MagicMock(id=500, symbol="NIFTY", interval="5m", override_action="SKIP", created_ts=datetime.utcnow())
        mock_get_ov.return_value = mock_ov
        
        res, _ = execute_latest_decisions_for_symbols(["NIFTY"], "5m")
        assert res[0]["dispatch"]["registered"] is True
        assert res[0]["dispatch"]["duplicate"] is False
