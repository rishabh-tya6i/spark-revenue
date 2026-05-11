import pytest
from unittest.mock import patch, MagicMock
from backend.orchestration.inference_runner import (
    run_price_inference_for_symbols,
    run_rl_inference_for_symbols,
    compute_decisions_for_symbols,
    summarize_inference_results
)

def test_run_price_inference_helper():
    with patch("backend.orchestration.inference_runner.predict_price_core") as mock_predict:
        # 1. Success
        mock_predict.return_value = MagicMock(label="UP", probabilities={"UP": 0.9}, model_version="v1")
        res = run_price_inference_for_symbols(["NIFTY"], "5m")
        assert len(res) == 1
        assert res[0]["status"] == "success"
        assert res[0]["label"] == "UP"
        
        # 2. Failure
        mock_predict.side_effect = Exception("cuda out of memory")
        res = run_price_inference_for_symbols(["CRASH"], "5m")
        assert res[0]["status"] == "failed"
        assert "cuda" in res[0]["error"]

def test_run_rl_inference_helper():
    with patch("backend.orchestration.inference_runner.get_rl_action_core") as mock_act:
        mock_act.return_value = MagicMock(action="BUY", action_index=2, confidence=0.8, policy_version="v2")
        res = run_rl_inference_for_symbols(["NIFTY"], "5m")
        assert len(res) == 1
        assert res[0]["status"] == "success"
        assert res[0]["action"] == "BUY"

def test_compute_decisions_helper():
    with patch("backend.orchestration.inference_runner.DecisionEngineService") as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.compute_decision_core.return_value = MagicMock(
            decision=MagicMock(id=99, decision_label="BULLISH", decision_score=0.85),
            alert={"type": "X"}
        )
        
        res = compute_decisions_for_symbols(["NIFTY"], "5m")
        assert len(res) == 1
        assert res[0]["status"] == "success"
        assert res[0]["decision_label"] == "BULLISH"
        assert res[0]["alert_created"] is True

def test_summarize_inference_results():
    price = [{"status": "success"}, {"status": "failed"}]
    rl = [{"status": "success"}]
    dec = [{"status": "success"}, {"status": "success"}]
    
    summary = summarize_inference_results(price, rl, dec)
    assert summary["price_prediction"]["total"] == 2
    assert summary["price_prediction"]["failed"] == 1
    assert summary["rl_action"]["success"] == 1
    assert summary["decision"]["total"] == 2
