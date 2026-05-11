import pytest
from unittest.mock import patch
from backend.orchestration.execution_guardrails import (
    parse_allowed_actions,
    evaluate_execution_guardrails,
    build_execution_guardrail_summary
)

def test_parse_allowed_actions():
    assert parse_allowed_actions("BUY,SELL") == ["BUY", "SELL"]
    assert parse_allowed_actions(" buy, sell ") == ["BUY", "SELL"]
    assert parse_allowed_actions("") == ["BUY", "SELL"]
    assert parse_allowed_actions(None) == ["BUY", "SELL"]
    assert parse_allowed_actions("BUY") == ["BUY"]

@patch("backend.orchestration.execution_guardrails.settings")
def test_evaluate_execution_guardrails_disabled(mock_settings):
    mock_settings.EXECUTION_ENABLED = False
    mock_settings.EXECUTION_MAX_SYMBOLS_PER_RUN = 5
    mock_settings.EXECUTION_ALLOWED_ACTIONS = "BUY,SELL"
    
    details = [
        {"symbol": "NIFTY", "ready": True, "rl_action": "BUY"},
        {"symbol": "SENSEX", "ready": True, "rl_action": "SELL"}
    ]
    
    result = evaluate_execution_guardrails(details)
    assert result["execution_enabled"] is False
    assert result["allowed_symbols"] == []
    assert len(result["blocked_symbols"]) == 2
    assert result["blocked_symbols"][0]["reason"] == "execution_disabled"

@patch("backend.orchestration.execution_guardrails.settings")
def test_evaluate_execution_guardrails_allowed_actions(mock_settings):
    mock_settings.EXECUTION_ENABLED = True
    mock_settings.EXECUTION_MAX_SYMBOLS_PER_RUN = 5
    mock_settings.EXECUTION_ALLOWED_ACTIONS = "BUY"
    
    details = [
        {"symbol": "NIFTY", "ready": True, "rl_action": "BUY"},
        {"symbol": "SENSEX", "ready": True, "rl_action": "SELL"}, # Disallowed
        {"symbol": "BANKNIFTY", "ready": True, "rl_action": "HOLD"} # Disallowed
    ]
    
    result = evaluate_execution_guardrails(details)
    assert result["allowed_symbols"] == ["NIFTY"]
    assert len(result["blocked_symbols"]) == 2
    assert result["blocked_symbols"][0]["symbol"] == "SENSEX"
    assert result["blocked_symbols"][0]["reason"] == "disallowed_action"

@patch("backend.orchestration.execution_guardrails.settings")
def test_evaluate_execution_guardrails_max_symbols(mock_settings):
    mock_settings.EXECUTION_ENABLED = True
    mock_settings.EXECUTION_MAX_SYMBOLS_PER_RUN = 2
    mock_settings.EXECUTION_ALLOWED_ACTIONS = "BUY,SELL"
    
    details = [
        {"symbol": "NIFTY", "ready": True, "rl_action": "BUY"},
        {"symbol": "SENSEX", "ready": True, "rl_action": "SELL"},
        {"symbol": "BANKNIFTY", "ready": True, "rl_action": "BUY"} # Blocked by cap
    ]
    
    result = evaluate_execution_guardrails(details)
    assert result["allowed_symbols"] == ["NIFTY", "SENSEX"]
    assert len(result["blocked_symbols"]) == 1
    assert result["blocked_symbols"][0]["symbol"] == "BANKNIFTY"
    assert result["blocked_symbols"][0]["reason"] == "max_symbols_cap"

def test_build_execution_guardrail_summary():
    res = {
        "execution_enabled": True,
        "allowed_actions": ["BUY"],
        "max_symbols_per_run": 5,
        "allowed_symbols": ["NIFTY"],
        "blocked_symbols": [{"symbol": "SENSEX", "reason": "disallowed_action"}]
    }
    summary = build_execution_guardrail_summary(res)
    assert summary["allowed_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["execution_enabled"] is True
