"""
Tests for AI Guardrails

Tests rate limiting, validation, and secret redaction.
"""
import pytest
import time
from controller_app.ai.guardrails import (
    Guardrails,
    GuardrailLimits,
    RateLimiter,
    redact_secrets,
    redact_secrets_from_dict,
    safe_format_exception,
)


def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = RateLimiter(max_per_minute=5)
    
    # Should allow first 5 executions
    for i in range(5):
        allowed, error = limiter.check_and_record()
        assert allowed, f"Execution {i} should be allowed"
        assert error is None
    
    # 6th execution should be blocked
    allowed, error = limiter.check_and_record()
    assert not allowed
    assert "Rate limit exceeded" in error


def test_rate_limiter_reset():
    """Test rate limiter reset."""
    limiter = RateLimiter(max_per_minute=3)
    
    # Use up all executions
    for _ in range(3):
        limiter.check_and_record()
    
    # Should be blocked
    allowed, _ = limiter.check_and_record()
    assert not allowed
    
    # Reset and try again
    limiter.reset()
    allowed, error = limiter.check_and_record()
    assert allowed
    assert error is None


def test_rate_limiter_get_remaining():
    """Test getting remaining executions."""
    limiter = RateLimiter(max_per_minute=10)
    
    assert limiter.get_remaining() == 10
    
    limiter.check_and_record()
    assert limiter.get_remaining() == 9
    
    for _ in range(5):
        limiter.check_and_record()
    assert limiter.get_remaining() == 4


def test_guardrails_rate_limit():
    """Test guardrails rate limiting."""
    limits = GuardrailLimits(max_tool_executions_per_minute=3, max_tool_executions_per_query=10)
    guardrails = Guardrails(limits)
    
    # Should allow first 3 executions
    for i in range(3):
        error = guardrails.check_rate_limit()
        assert error is None, f"Execution {i} should be allowed"
    
    # 4th execution should be blocked
    error = guardrails.check_rate_limit()
    assert error is not None
    assert "Rate limit exceeded" in error


def test_guardrails_query_limit():
    """Test per-query execution limit."""
    limits = GuardrailLimits(max_tool_executions_per_minute=100, max_tool_executions_per_query=5)
    guardrails = Guardrails(limits)
    
    # Should allow first 5 executions
    for i in range(5):
        error = guardrails.check_rate_limit()
        assert error is None, f"Execution {i} should be allowed"
    
    # 6th execution should be blocked
    error = guardrails.check_rate_limit()
    assert error is not None
    assert "Too many tool executions" in error
    
    # Reset and try again
    guardrails.reset_query()
    error = guardrails.check_rate_limit()
    assert error is None


def test_guardrails_validate_notes_count():
    """Test note count validation."""
    limits = GuardrailLimits(max_notes_per_operation=5)
    guardrails = Guardrails(limits)
    
    # Valid number of notes
    notes = [{"pitch": 60, "velocity": 100, "duration": 1.0}] * 5
    error = guardrails.validate_notes(notes)
    assert error is None
    
    # Too many notes
    notes = [{"pitch": 60, "velocity": 100, "duration": 1.0}] * 6
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "Too many notes" in error


def test_guardrails_validate_notes_pitch():
    """Test note pitch validation."""
    guardrails = Guardrails()
    
    # Valid pitch
    notes = [{"pitch": 60, "velocity": 100, "duration": 1.0}]
    error = guardrails.validate_notes(notes)
    assert error is None
    
    # Pitch too low
    notes = [{"pitch": -1, "velocity": 100, "duration": 1.0}]
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "pitch" in error.lower()
    
    # Pitch too high
    notes = [{"pitch": 128, "velocity": 100, "duration": 1.0}]
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "pitch" in error.lower()


def test_guardrails_validate_notes_velocity():
    """Test note velocity validation."""
    guardrails = Guardrails()
    
    # Valid velocity
    notes = [{"pitch": 60, "velocity": 100, "duration": 1.0}]
    error = guardrails.validate_notes(notes)
    assert error is None
    
    # Velocity too low
    notes = [{"pitch": 60, "velocity": 0, "duration": 1.0}]
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "velocity" in error.lower()
    
    # Velocity too high
    notes = [{"pitch": 60, "velocity": 128, "duration": 1.0}]
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "velocity" in error.lower()


def test_guardrails_validate_notes_duration():
    """Test note duration validation."""
    guardrails = Guardrails()
    
    # Valid duration
    notes = [{"pitch": 60, "velocity": 100, "duration": 1.0}]
    error = guardrails.validate_notes(notes)
    assert error is None
    
    # Duration too short
    notes = [{"pitch": 60, "velocity": 100, "duration": 0.001}]
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "duration" in error.lower()
    
    # Duration too long
    notes = [{"pitch": 60, "velocity": 100, "duration": 100.0}]
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "duration" in error.lower()


def test_guardrails_validate_parameter():
    """Test parameter validation."""
    guardrails = Guardrails()
    
    # Valid parameter
    error = guardrails.validate_parameter(10, 0.5)
    assert error is None
    
    # Negative index
    error = guardrails.validate_parameter(-1, 0.5)
    assert error is not None
    assert "index" in error.lower()
    
    # Index too high
    error = guardrails.validate_parameter(2000, 0.5)
    assert error is not None
    assert "index" in error.lower()
    
    # Value too low
    error = guardrails.validate_parameter(10, -0.1)
    assert error is not None
    assert "value" in error.lower()
    
    # Value too high
    error = guardrails.validate_parameter(10, 1.5)
    assert error is not None
    assert "value" in error.lower()


def test_guardrails_safe_mode():
    """Test safe mode restrictions."""
    # Normal mode
    guardrails = Guardrails()
    assert guardrails.limits.max_notes_per_operation == 128
    assert guardrails.limits.max_tool_executions_per_query == 16
    
    # Enable safe mode
    guardrails.enable_safe_mode(True)
    assert guardrails.limits.max_notes_per_operation == 64
    assert guardrails.limits.max_tool_executions_per_query == 8
    
    # Verify stricter limits are enforced
    notes = [{"pitch": 60, "velocity": 100, "duration": 1.0}] * 65
    error = guardrails.validate_notes(notes)
    assert error is not None
    assert "Too many notes" in error


def test_guardrails_check_destructive_patterns():
    """Test destructive pattern detection."""
    guardrails = Guardrails()
    
    # Non-destructive operation
    is_dest, reason = guardrails.check_destructive_patterns("set_param", {"value": 0.5})
    assert not is_dest
    
    # Destructive patterns
    destructive_cases = [
        ("set_param", {"action": "delete all"}),
        ("set_note_batch", {"notes": "clear all"}),
        ("mixer", {"command": "reset all"}),
    ]
    
    for tool_name, args in destructive_cases:
        is_dest, reason = guardrails.check_destructive_patterns(tool_name, args)
        assert is_dest, f"Should detect destructive pattern in {tool_name}"
        assert len(reason) > 0


def test_redact_secrets_openai_key():
    """Test OpenAI API key redaction."""
    text = "My API key is sk-abc123def456ghi789jkl000"
    redacted = redact_secrets(text)
    assert "sk-abc123def456ghi789jkl000" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_secrets_generic_key():
    """Test generic API key redaction."""
    text = 'api_key: "abcdef1234567890abcdef1234567890"'
    redacted = redact_secrets(text)
    assert "abcdef1234567890abcdef1234567890" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_secrets_bearer_token():
    """Test Bearer token redaction."""
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    redacted = redact_secrets(text)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_secrets_from_dict():
    """Test secret redaction from dictionary."""
    data = {
        "query": "Set the cutoff to 0.7",
        "api_key": "sk-secret123456",
        "config": {
            "openai_token": "tok-abc123",
            "model": "gpt-4o-mini"
        }
    }
    
    redacted = redact_secrets_from_dict(data)
    
    # Check that secrets are redacted
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["config"]["openai_token"] == "[REDACTED]"
    
    # Check that non-sensitive data is preserved
    assert redacted["query"] == "Set the cutoff to 0.7"
    assert redacted["config"]["model"] == "gpt-4o-mini"


def test_redact_secrets_from_dict_nested():
    """Test secret redaction from nested dictionary."""
    data = {
        "providers": [
            {"name": "openai", "api_key": "sk-123"},
            {"name": "anthropic", "token": "ant-456"}
        ]
    }
    
    redacted = redact_secrets_from_dict(data)
    
    assert redacted["providers"][0]["api_key"] == "[REDACTED]"
    assert redacted["providers"][1]["token"] == "[REDACTED]"
    assert redacted["providers"][0]["name"] == "openai"


def test_safe_format_exception():
    """Test exception formatting with secret redaction."""
    # Exception with API key
    try:
        raise ValueError("API call failed with key sk-secret123456")
    except ValueError as e:
        formatted = safe_format_exception(e)
        assert "sk-secret123456" not in formatted
        assert "[REDACTED]" in formatted
        assert "API call failed" in formatted


def test_guardrails_limits_initialization():
    """Test GuardrailLimits initialization."""
    # Default limits
    limits = GuardrailLimits()
    assert limits.max_notes_per_operation == 128
    assert limits.max_param_value == 1.0
    assert limits.safe_mode is False
    
    # Custom limits
    limits = GuardrailLimits(max_notes_per_operation=50, safe_mode=False)
    assert limits.max_notes_per_operation == 50
    
    # Safe mode limits
    limits = GuardrailLimits(safe_mode=True)
    assert limits.max_notes_per_operation == 64
    assert limits.max_tool_executions_per_query == 8


def test_guardrails_multiple_violations():
    """Test handling multiple violations."""
    guardrails = Guardrails()
    
    # Multiple notes with various violations
    notes = [
        {"pitch": 60, "velocity": 100, "duration": 1.0},  # Valid
        {"pitch": 200, "velocity": 100, "duration": 1.0},  # Invalid pitch
        {"pitch": 60, "velocity": 0, "duration": 1.0},     # Invalid velocity
        {"pitch": 60, "velocity": 100, "duration": 0.001}, # Invalid duration
    ]
    
    # Should catch first violation (pitch)
    error = guardrails.validate_notes(notes)
    assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
