"""
Tests for Telemetry Module

Tests local logging, network opt-in, and event tracking.
"""
import pytest
import tempfile
import json
from pathlib import Path
from controller_app.telemetry import Telemetry, init_telemetry


def test_telemetry_initialization():
    """Test telemetry initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        assert telemetry.enabled is True
        assert telemetry.network_enabled is False  # Disabled by default
        assert log_dir.exists()


def test_telemetry_disabled():
    """Test that disabled telemetry doesn't log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=False)
        
        # Try to log an event
        telemetry.log_agent_query("test", "openai", True)
        
        # No log file should be created
        log_files = list(log_dir.glob("*.jsonl"))
        assert len(log_files) == 0


def test_log_agent_query():
    """Test logging agent queries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Log a query
        telemetry.log_agent_query("Set the cutoff to 0.7", "openai", True)
        
        # Read log file
        log_files = list(log_dir.glob("*.jsonl"))
        assert len(log_files) == 1
        
        with open(log_files[0]) as f:
            entry = json.loads(f.readline())
        
        assert entry["event_type"] == "agent_query"
        assert entry["data"]["provider"] == "openai"
        assert entry["data"]["dry_run"] is True
        assert entry["data"]["query_length"] == 21


def test_log_agent_query_truncation():
    """Test that long queries are truncated in logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Log a long query
        long_query = "A" * 100
        telemetry.log_agent_query(long_query, "openai", True)
        
        # Read log file
        log_files = list(log_dir.glob("*.jsonl"))
        with open(log_files[0]) as f:
            entry = json.loads(f.readline())
        
        # Query should be truncated to 50 chars + "..."
        assert len(entry["data"]["query_preview"]) == 53
        assert entry["data"]["query_preview"].endswith("...")


def test_log_tool_execution():
    """Test logging tool executions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Log successful execution
        telemetry.log_tool_execution("set_param", True)
        
        # Log failed execution
        telemetry.log_tool_execution("set_param", False, "Parameter out of range")
        
        # Read log file
        log_files = list(log_dir.glob("*.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        
        # Check success entry
        success_entry = json.loads(lines[0])
        assert success_entry["event_type"] == "tool_execution"
        assert success_entry["data"]["tool_name"] == "set_param"
        assert success_entry["data"]["success"] is True
        assert success_entry["data"]["error"] is None
        
        # Check failure entry
        failure_entry = json.loads(lines[1])
        assert failure_entry["data"]["success"] is False
        assert failure_entry["data"]["error"] == "Parameter out of range"


def test_log_error():
    """Test logging errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Log an error
        telemetry.log_error("rate_limit", "Rate limit exceeded", {"remaining": 0})
        
        # Read log file
        log_files = list(log_dir.glob("*.jsonl"))
        with open(log_files[0]) as f:
            entry = json.loads(f.readline())
        
        assert entry["event_type"] == "error"
        assert entry["data"]["error_type"] == "rate_limit"
        assert entry["data"]["message"] == "Rate limit exceeded"
        assert entry["data"]["context"]["remaining"] == 0


def test_network_telemetry_opt_in():
    """Test network telemetry opt-in."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Should be disabled by default
        assert telemetry.network_enabled is False
        
        # Enable network telemetry
        telemetry.enable_network_telemetry(True)
        assert telemetry.network_enabled is True
        
        # Disable network telemetry
        telemetry.enable_network_telemetry(False)
        assert telemetry.network_enabled is False


def test_multiple_events():
    """Test logging multiple events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Log multiple events
        telemetry.log_agent_query("query 1", "openai", True)
        telemetry.log_tool_execution("set_param", True)
        telemetry.log_tool_execution("transport", True)
        telemetry.log_error("test", "test error")
        
        # Read log file
        log_files = list(log_dir.glob("*.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
        
        assert len(lines) == 4
        
        # Verify each entry is valid JSON
        for line in lines:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "event_type" in entry
            assert "data" in entry


def test_init_telemetry_global():
    """Test global telemetry initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        
        # Initialize global instance
        telemetry = init_telemetry(log_dir=log_dir, enabled=True)
        
        assert telemetry.enabled is True
        assert log_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
