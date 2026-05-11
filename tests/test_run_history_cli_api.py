import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.orchestration.run_history import orchestration_run_to_dict

client = TestClient(app)

@pytest.fixture
def mock_record():
    record = MagicMock()
    record.id = 123
    record.run_type = "cycle"
    record.status = "completed"
    record.mode = "explicit"
    record.interval = "5m"
    record.selected_symbols_count = 2
    record.ready_symbols_count = 1
    record.success_count = 1
    record.skipped_count = 0
    record.failed_count = 0
    record.summary_json = '{"test": "data"}'
    from datetime import datetime
    record.created_ts = datetime.utcnow()
    return record

def test_get_runs_api(mock_record):
    with patch("backend.orchestration.app.list_orchestration_runs", return_value=[mock_record]):
        response = client.get("/orchestration/runs?run_type=cycle&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 123
        assert data[0]["run_type"] == "cycle"

def test_get_run_detail_api(mock_record):
    with patch("backend.orchestration.app.get_orchestration_run", return_value=mock_record):
        response = client.get("/orchestration/runs/123")
        assert response.status_code == 200
        assert response.json()["id"] == 123

def test_trigger_returns_run_record_id():
    # Mocking run_operational_cycle_core which we updated to return run_record_id
    mock_result = {
        "status": "completed",
        "run_record_id": 456,
        "summary": {}
    }
    with patch("backend.orchestration.app.run_operational_cycle_core", return_value=mock_result):
        response = client.post("/orchestration/run-cycle")
        assert response.status_code == 200
        assert response.json()["run_record_id"] == 456

def test_list_runs_cli(mock_record):
    from backend.orchestration.cli import main
    import sys
    
    with patch("backend.orchestration.cli.list_orchestration_runs", return_value=[mock_record]), \
         patch.object(sys, 'argv', ['cli.py', 'list-runs', '--run-type', 'cycle']), \
         patch('builtins.print') as mock_print:
        main()
        # Verify print was called (headers + 1 record)
        assert mock_print.call_count >= 2

def test_show_run_cli(mock_record):
    from backend.orchestration.cli import main
    import sys
    
    with patch("backend.orchestration.cli.get_orchestration_run", return_value=mock_record), \
         patch.object(sys, 'argv', ['cli.py', 'show-run', '--run-id', '123']), \
         patch('builtins.print') as mock_print:
        main()
        # Verify print was called for the record details
        assert mock_print.call_count >= 5
