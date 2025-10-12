"""
Integration Tests for Safety Features

Tests the complete integration of telemetry, guardrails, and agent.
"""
import pytest
import tempfile
from pathlib import Path
from controller_app.telemetry import Telemetry
from controller_app.ai.guardrails import Guardrails, GuardrailLimits
from controller_app.ai.agent import run_agent, AgentError
from controller_app.ai.providers.base import ChatResponse, ToolCall
from controller_app.ai.templates.tool_schemas import get_tool_schemas


class MockProvider:
    """Mock AI provider for testing."""
    
    def __init__(self, tool_calls=None, content="Here's what I'll do:"):
        self.tool_calls = tool_calls or []
        self.content = content
    
    def chat(self, messages, tools=None, tool_choice=None, stream=False):
        return ChatResponse(
            content=self.content,
            tool_calls=self.tool_calls,
            usage={"input_tokens": 100, "output_tokens": 50},
        )


def test_telemetry_logs_agent_query():
    """Test that telemetry logs agent queries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Create simple provider
        provider = MockProvider(tool_calls=[
            ToolCall(
                name="set_param",
                arguments={"plugin_ref": "0:0", "index": 5, "value01": 0.5},
            ),
        ])
        
        # Run agent (will trigger telemetry logging)
        tools = get_tool_schemas()
        
        # Temporarily replace global telemetry
        from controller_app import telemetry as telemetry_module
        old_telemetry = telemetry_module._telemetry
        telemetry_module._telemetry = telemetry
        
        try:
            plan = run_agent(
                query="Set parameter 5 to 0.5",
                provider=provider,
                tools=tools,
                dry_run=True,
            )
            
            # Check that log file was created
            log_files = list(log_dir.glob("*.jsonl"))
            assert len(log_files) == 1, "Should create telemetry log"
            
        finally:
            # Restore original telemetry
            telemetry_module._telemetry = old_telemetry


def test_guardrails_enforced_in_agent():
    """Test that guardrails are enforced in agent execution."""
    # Create guardrails with strict limits
    limits = GuardrailLimits(max_notes_per_operation=2)
    guardrails = Guardrails(limits)
    
    # Create provider that tries to add too many notes
    provider = MockProvider(tool_calls=[
        ToolCall(
            name="set_note_batch",
            arguments={
                "channel_ref": "0",
                "notes": [
                    {"pitch": 60, "velocity": 100, "duration": 1.0, "start": 0.0},
                    {"pitch": 64, "velocity": 100, "duration": 1.0, "start": 1.0},
                    {"pitch": 67, "velocity": 100, "duration": 1.0, "start": 2.0},
                ],
            },
        ),
    ])
    
    # Replace global guardrails
    from controller_app.ai import guardrails as guardrails_module
    old_guardrails = guardrails_module._guardrails
    guardrails_module._guardrails = guardrails
    
    try:
        tools = get_tool_schemas()
        
        # Should raise AgentError due to too many notes
        with pytest.raises(AgentError, match="Too many notes"):
            run_agent(
                query="Add notes",
                provider=provider,
                tools=tools,
                dry_run=True,
            )
    finally:
        # Restore original guardrails
        guardrails_module._guardrails = old_guardrails


def test_rate_limiting_enforced_in_agent_execution():
    """Test that rate limiting prevents excessive tool executions."""
    # Create guardrails with very low rate limit
    limits = GuardrailLimits(
        max_tool_executions_per_minute=2,
        max_tool_executions_per_query=10
    )
    guardrails = Guardrails(limits)
    
    # Mock IPC client
    class MockIPCClient:
        def __init__(self):
            self.calls = []
        
        def set_param(self, plugin_ref, index, value01):
            self.calls.append(("set_param", plugin_ref, index, value01))
            return {"success": True}
    
    ipc_client = MockIPCClient()
    
    # Create provider with multiple tool calls
    provider = MockProvider(tool_calls=[
        ToolCall(
            name="set_param",
            arguments={"plugin_ref": "0:0", "index": 1, "value01": 0.5},
        ),
        ToolCall(
            name="set_param",
            arguments={"plugin_ref": "0:0", "index": 2, "value01": 0.6},
        ),
        ToolCall(
            name="set_param",
            arguments={"plugin_ref": "0:0", "index": 3, "value01": 0.7},
        ),
    ])
    
    # Replace global guardrails
    from controller_app.ai import guardrails as guardrails_module
    old_guardrails = guardrails_module._guardrails
    guardrails_module._guardrails = guardrails
    
    try:
        tools = get_tool_schemas()
        
        # Run agent (should hit rate limit on 3rd execution)
        plan = run_agent(
            query="Set parameters",
            provider=provider,
            tools=tools,
            ipc_client=ipc_client,
            dry_run=False,
        )
        
        # First 2 should succeed, 3rd should be rate limited
        assert len(plan.actions) == 3
        assert plan.actions[0].error is None
        assert plan.actions[1].error is None
        assert plan.actions[2].error is not None
        assert "Rate limit exceeded" in plan.actions[2].error
        
        # Only 2 IPC calls should have been made
        assert len(ipc_client.calls) == 2
        
    finally:
        # Restore original guardrails
        guardrails_module._guardrails = old_guardrails


def test_safe_mode_reduces_limits():
    """Test that safe mode reduces operational limits."""
    # Create guardrails in normal mode
    guardrails = Guardrails()
    assert guardrails.limits.max_notes_per_operation == 128
    
    # Enable safe mode
    guardrails.enable_safe_mode(True)
    assert guardrails.limits.max_notes_per_operation == 64
    assert guardrails.limits.max_tool_executions_per_query == 8
    
    # Disable safe mode
    guardrails.enable_safe_mode(False)
    assert guardrails.limits.max_notes_per_operation == 128
    assert guardrails.limits.max_tool_executions_per_query == 16


def test_secret_redaction_in_agent_errors():
    """Test that secrets are redacted from agent error messages."""
    # Create provider that raises an error with a secret
    class ErrorProvider:
        def chat(self, messages, tools=None, tool_choice=None, stream=False):
            raise ValueError("API call failed with key sk-secret123456789012")
    
    provider = ErrorProvider()
    tools = get_tool_schemas()
    
    # Should raise AgentError with redacted message
    with pytest.raises(AgentError) as exc_info:
        run_agent(
            query="Test query",
            provider=provider,
            tools=tools,
            dry_run=True,
        )
    
    # Error message should be redacted
    error_message = str(exc_info.value)
    assert "sk-secret123456789012" not in error_message
    assert "[REDACTED]" in error_message


def test_network_telemetry_opt_in():
    """Test that network telemetry is opt-in only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "telemetry"
        telemetry = Telemetry(log_dir=log_dir, enabled=True)
        
        # Should be disabled by default
        assert telemetry.network_enabled is False
        
        # Enable network telemetry
        telemetry.enable_network_telemetry(True)
        assert telemetry.network_enabled is True
        
        # Disable again
        telemetry.enable_network_telemetry(False)
        assert telemetry.network_enabled is False


def test_guardrails_validate_destructive_patterns():
    """Test that destructive patterns are detected."""
    guardrails = Guardrails()
    
    # Non-destructive operation
    is_dest, reason = guardrails.check_destructive_patterns(
        "set_param",
        {"value": 0.5}
    )
    assert not is_dest
    
    # Destructive operation
    is_dest, reason = guardrails.check_destructive_patterns(
        "set_param",
        {"action": "delete all"}
    )
    assert is_dest
    assert "destructive" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
