# Safety Features - Telemetry and Guardrails

## Overview

This document describes the safety features implemented in PR #7, including opt-in telemetry, guardrails, and secret redaction.

## Features

### 1. Local-Only Telemetry (`controller_app/telemetry.py`)

**Key Features:**
- ✅ Local logging is **always enabled by default**
- ✅ Network telemetry is **disabled by default** (opt-in only)
- ✅ Logs are stored in `~/.fl-ai-producer/telemetry/events_YYYYMMDD.jsonl`
- ✅ Thread-safe logging with file locking

**What Gets Logged:**
- Agent queries (query length, provider, dry_run status)
- Tool executions (tool name, success/failure, errors)
- Errors (error type, message, context)

**Privacy:**
- Query content is truncated to first 50 characters in logs
- No network transmission unless explicitly opted-in via UI
- All secrets are automatically redacted from logs

**API:**
```python
from controller_app.telemetry import get_telemetry, init_telemetry

# Initialize (done automatically by app.py)
telemetry = init_telemetry(enabled=True)

# Enable network telemetry (opt-in)
telemetry.enable_network_telemetry(True)

# Log events
telemetry.log_agent_query("user query", "openai", dry_run=True)
telemetry.log_tool_execution("set_param", success=True)
telemetry.log_error("rate_limit", "Rate limit exceeded")
```

### 2. AI Guardrails (`controller_app/ai/guardrails.py`)

**Rate Limiting:**
- ✅ Maximum tool executions per minute (default: 60)
- ✅ Maximum tool executions per query (default: 16)
- ✅ Safe mode reduces limits by 50%

**Hard Limits:**
- ✅ Max notes per operation: 128 (64 in safe mode)
- ✅ Note pitch: 0-127 (MIDI standard)
- ✅ Note velocity: 1-127 (MIDI standard)
- ✅ Note duration: 0.01-64.0 bars
- ✅ Parameter values: 0.0-1.0 (normalized)
- ✅ Parameter index: 0-1024

**Destructive Pattern Detection:**
- ✅ Blocks operations with keywords: "delete all", "clear all", "reset all", etc.
- ✅ Prevents accidental data loss

**Secret Redaction:**
- ✅ OpenAI API keys (sk-*)
- ✅ Generic API keys
- ✅ Bearer tokens
- ✅ Sensitive dictionary keys (api_key, token, secret, password)

**API:**
```python
from controller_app.ai.guardrails import (
    get_guardrails, 
    redact_secrets,
    safe_format_exception
)

# Initialize (done automatically by app.py)
guardrails = get_guardrails()

# Enable safe mode
guardrails.enable_safe_mode(True)

# Check rate limits
error = guardrails.check_rate_limit()
if error:
    print(f"Rate limit exceeded: {error}")

# Validate notes
notes = [{"pitch": 60, "velocity": 100, "duration": 1.0}]
error = guardrails.validate_notes(notes)

# Redact secrets
safe_text = redact_secrets("API key: sk-abc123...")
safe_error = safe_format_exception(exception)
```

### 3. UI Toggles (AI Assistant Tab)

**New Settings Section:**
- ✅ **"Enable Network Telemetry (opt-in)"** checkbox
  - Disabled by default
  - Shows info: "📊 Local logging is always enabled. Network telemetry is opt-in only."
  
- ✅ **"Safe Mode (stricter limits)"** checkbox
  - Disabled by default
  - Shows info: "🛡️ Reduces max notes/operations and enforces stricter rate limits."

**User Feedback:**
- Status messages appear in the Results/Logs area when toggling settings
- Clear indicators show when safe mode or network telemetry is enabled

### 4. Integration with Agent

**Changes to `controller_app/ai/agent.py`:**
- ✅ Guardrails validation integrated into `_validate_tool_arguments()`
- ✅ Rate limiting checked before each tool execution
- ✅ Telemetry logging for queries, executions, and errors
- ✅ Secret redaction in all error messages
- ✅ Destructive pattern checking uses guardrails

**Safety Flow:**
1. User submits query → Logged to telemetry
2. Agent plans actions → Validated against guardrails
3. Actions executed → Rate limiting enforced
4. Results returned → Errors are redacted and logged

### 5. Tests (`controller_app/tests/test_guardrails.py`)

**20 comprehensive tests covering:**
- ✅ Rate limiter basic functionality
- ✅ Rate limiter reset and remaining count
- ✅ Guardrails rate limiting (per-minute and per-query)
- ✅ Note validation (count, pitch, velocity, duration)
- ✅ Parameter validation (index, value)
- ✅ Safe mode enforcement
- ✅ Destructive pattern detection
- ✅ Secret redaction (OpenAI keys, generic keys, Bearer tokens)
- ✅ Dictionary secret redaction (nested structures)
- ✅ Exception formatting with redaction

**All tests pass:** ✅ 20 passed, 0 failed

## Configuration

### Default Limits (Normal Mode)
```python
max_notes_per_operation = 128
max_tool_executions_per_minute = 60
max_tool_executions_per_query = 16
min_param_value = 0.0
max_param_value = 1.0
```

### Safe Mode Limits
```python
max_notes_per_operation = 64  # 50% reduction
max_tool_executions_per_minute = 30  # 50% reduction
max_tool_executions_per_query = 8  # 50% reduction
```

## Privacy Guarantees

1. **Local-Only by Default:**
   - All telemetry logs are stored locally in `~/.fl-ai-producer/telemetry/`
   - No network transmission unless explicitly enabled

2. **Opt-In Network Telemetry:**
   - User must explicitly check the "Enable Network Telemetry" checkbox
   - Clear UI indicators show telemetry status

3. **Secret Redaction:**
   - All API keys, tokens, and secrets are automatically redacted
   - Applies to logs, error messages, and telemetry events
   - Uses pattern matching to catch various formats

4. **Query Truncation:**
   - User queries are truncated to 50 characters in logs
   - Protects potentially sensitive user instructions

## Files Changed

### New Files:
- `controller_app/telemetry.py` - Telemetry module (201 lines)
- `controller_app/ai/guardrails.py` - Guardrails module (372 lines)
- `controller_app/tests/test_guardrails.py` - Test suite (358 lines)

### Modified Files:
- `controller_app/app.py` - Initialize telemetry and guardrails
- `controller_app/ai/agent.py` - Integrate guardrails and telemetry
- `controller_app/ui/main_window.py` - Add UI toggles and handlers

## Usage Examples

### Example 1: Normal Operation
```python
# App starts with telemetry (local-only) and guardrails
# User makes query → Logged locally
# Actions validated → Rate limits checked
# Execution proceeds → Success/errors logged
```

### Example 2: Safe Mode Enabled
```python
# User enables safe mode via UI
# Max notes reduced from 128 to 64
# Rate limits reduced by 50%
# Stricter validation enforced
```

### Example 3: Rate Limit Exceeded
```python
# User triggers many operations quickly
# Rate limiter detects > 60 operations/min
# Execution blocked with error message
# Error logged to telemetry
```

### Example 4: Secret Redaction
```python
# Exception contains API key
# Exception message: "Failed with key sk-abc123..."
# Redacted message: "Failed with key [REDACTED]"
# Safe message shown to user and logged
```

## Future Enhancements

Potential improvements for future PRs:
- [ ] Configurable rate limits via UI
- [ ] Telemetry dashboard for viewing local logs
- [ ] Export telemetry logs for analysis
- [ ] More granular safe mode options
- [ ] Undo/redo for destructive operations
- [ ] Action confirmation dialogs for risky operations
