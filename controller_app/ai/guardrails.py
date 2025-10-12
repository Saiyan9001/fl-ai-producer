"""
AI Guardrails - Safety and Rate Limiting

Provides:
- Hard limits on operations (max notes, parameter ranges)
- Rate limiting for tool executions
- Secret redaction from logs and prompts
"""
import re
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


# API key patterns to redact
API_KEY_PATTERNS = [
    r'sk-[a-zA-Z0-9_-]{10,}',  # OpenAI API keys (sk- prefix with 10+ chars)
    r'api[_-]?key["\s:=]+[a-zA-Z0-9]{10,}',  # Generic API keys
    r'Bearer\s+[a-zA-Z0-9\-_.]{20,}',  # Bearer tokens
]


@dataclass
class GuardrailLimits:
    """Configuration for guardrail limits."""
    
    # Note limits
    max_notes_per_operation: int = 128
    min_note_pitch: int = 0
    max_note_pitch: int = 127
    min_note_velocity: int = 1
    max_note_velocity: int = 127
    min_note_duration: float = 0.01  # 10ms minimum
    max_note_duration: float = 64.0  # 64 bars maximum
    
    # Parameter limits
    min_param_value: float = 0.0
    max_param_value: float = 1.0
    max_param_index: int = 1024  # Maximum parameter index
    
    # Rate limiting
    max_tool_executions_per_minute: int = 60
    max_tool_executions_per_query: int = 16
    
    # Safe mode (stricter limits)
    safe_mode: bool = False
    
    def __post_init__(self):
        """Apply safe mode restrictions if enabled."""
        if self.safe_mode:
            # Stricter limits in safe mode
            self.max_notes_per_operation = 64
            self.max_note_duration = 16.0
            self.max_tool_executions_per_minute = 30
            self.max_tool_executions_per_query = 8


class RateLimiter:
    """Rate limiter for tool executions."""
    
    def __init__(self, max_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_per_minute: Maximum executions per minute
        """
        self.max_per_minute = max_per_minute
        self.executions: List[datetime] = []
        self._lock = threading.Lock()
    
    def check_and_record(self) -> Tuple[bool, Optional[str]]:
        """
        Check if execution is allowed and record it.
        
        Returns:
            Tuple of (allowed, error_message)
        """
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)
            
            # Remove old executions
            self.executions = [ts for ts in self.executions if ts > cutoff]
            
            # Check limit
            if len(self.executions) >= self.max_per_minute:
                return False, f"Rate limit exceeded: {self.max_per_minute} executions per minute"
            
            # Record execution
            self.executions.append(now)
            return True, None
    
    def get_remaining(self) -> int:
        """
        Get remaining executions in current window.
        
        Returns:
            Number of remaining executions
        """
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)
            self.executions = [ts for ts in self.executions if ts > cutoff]
            return max(0, self.max_per_minute - len(self.executions))
    
    def reset(self):
        """Reset the rate limiter."""
        with self._lock:
            self.executions = []


class Guardrails:
    """
    Guardrails for AI agent operations.
    
    Enforces safety limits and rate limiting.
    """
    
    def __init__(self, limits: Optional[GuardrailLimits] = None):
        """
        Initialize guardrails.
        
        Args:
            limits: Guardrail limits configuration
        """
        self.limits = limits or GuardrailLimits()
        self.rate_limiter = RateLimiter(self.limits.max_tool_executions_per_minute)
        self.query_execution_count = 0
        self._lock = threading.Lock()
    
    def enable_safe_mode(self, enabled: bool = True):
        """
        Enable or disable safe mode.
        
        Safe mode applies stricter limits.
        
        Args:
            enabled: Whether to enable safe mode
        """
        self.limits.safe_mode = enabled
        # Recreate limits with safe mode
        self.limits = GuardrailLimits(safe_mode=enabled)
        # Update rate limiter
        self.rate_limiter = RateLimiter(self.limits.max_tool_executions_per_minute)
        logger.info(f"Safe mode {'enabled' if enabled else 'disabled'}")
    
    def reset_query(self):
        """Reset per-query execution counter."""
        with self._lock:
            self.query_execution_count = 0
    
    def check_rate_limit(self) -> Optional[str]:
        """
        Check rate limits before execution.
        
        Returns:
            Error message if limit exceeded, None otherwise
        """
        # Check per-minute rate limit
        allowed, error = self.rate_limiter.check_and_record()
        if not allowed:
            return error
        
        # Check per-query limit
        with self._lock:
            self.query_execution_count += 1
            if self.query_execution_count > self.limits.max_tool_executions_per_query:
                return f"Too many tool executions in single query (max: {self.limits.max_tool_executions_per_query})"
        
        return None
    
    def validate_notes(self, notes: List[Dict[str, Any]]) -> Optional[str]:
        """
        Validate note batch against guardrails.
        
        Args:
            notes: List of note dictionaries
            
        Returns:
            Error message if validation fails, None otherwise
        """
        # Check number of notes
        if len(notes) > self.limits.max_notes_per_operation:
            return f"Too many notes: {len(notes)} (max: {self.limits.max_notes_per_operation})"
        
        # Validate each note
        for i, note in enumerate(notes):
            # Check pitch
            pitch = note.get("pitch")
            if pitch is not None:
                if pitch < self.limits.min_note_pitch or pitch > self.limits.max_note_pitch:
                    return f"Note {i} pitch {pitch} out of range [{self.limits.min_note_pitch}, {self.limits.max_note_pitch}]"
            
            # Check velocity
            velocity = note.get("velocity")
            if velocity is not None:
                if velocity < self.limits.min_note_velocity or velocity > self.limits.max_note_velocity:
                    return f"Note {i} velocity {velocity} out of range [{self.limits.min_note_velocity}, {self.limits.max_note_velocity}]"
            
            # Check duration
            duration = note.get("duration")
            if duration is not None:
                if duration < self.limits.min_note_duration or duration > self.limits.max_note_duration:
                    return f"Note {i} duration {duration} out of range [{self.limits.min_note_duration}, {self.limits.max_note_duration}]"
        
        return None
    
    def validate_parameter(self, index: int, value: float) -> Optional[str]:
        """
        Validate parameter setting against guardrails.
        
        Args:
            index: Parameter index
            value: Parameter value (normalized 0-1)
            
        Returns:
            Error message if validation fails, None otherwise
        """
        # Check parameter index
        if index < 0 or index > self.limits.max_param_index:
            return f"Parameter index {index} out of range [0, {self.limits.max_param_index}]"
        
        # Check parameter value
        if value < self.limits.min_param_value or value > self.limits.max_param_value:
            return f"Parameter value {value} out of range [{self.limits.min_param_value}, {self.limits.max_param_value}]"
        
        return None
    
    def check_destructive_patterns(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check for potentially destructive patterns.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Tuple of (is_destructive, reason)
        """
        destructive_keywords = [
            "delete all", "remove all", "clear all", "reset all",
            "erase", "wipe", "destroy"
        ]
        
        # Check arguments for destructive keywords
        for key, value in arguments.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for keyword in destructive_keywords:
                    if keyword in value_lower:
                        return True, f"Potentially destructive operation: '{keyword}' in {key}"
        
        return False, ""


def redact_secrets(text: str) -> str:
    """
    Redact API keys and secrets from text.
    
    Args:
        text: Text potentially containing secrets
        
    Returns:
        Text with secrets redacted
    """
    redacted = text
    
    # Redact based on patterns
    for pattern in API_KEY_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
    
    return redacted


def redact_secrets_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively redact secrets from dictionary.
    
    Args:
        data: Dictionary potentially containing secrets
        
    Returns:
        Dictionary with secrets redacted
    """
    redacted = {}
    
    sensitive_keys = ["api_key", "apikey", "api-key", "token", "secret", "password", "key"]
    
    for key, value in data.items():
        # Check if key is sensitive
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, str):
            redacted[key] = redact_secrets(value)
        elif isinstance(value, dict):
            redacted[key] = redact_secrets_from_dict(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_secrets_from_dict(item) if isinstance(item, dict) else
                redact_secrets(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            redacted[key] = value
    
    return redacted


def safe_format_exception(exception: Exception) -> str:
    """
    Format exception message with secrets redacted.
    
    Args:
        exception: Exception to format
        
    Returns:
        Safe exception message
    """
    message = str(exception)
    return redact_secrets(message)


# Global guardrails instance
_guardrails: Optional[Guardrails] = None


def get_guardrails() -> Guardrails:
    """
    Get the global guardrails instance.
    
    Returns:
        Global guardrails instance
    """
    global _guardrails
    if _guardrails is None:
        _guardrails = Guardrails()
    return _guardrails


def init_guardrails(limits: Optional[GuardrailLimits] = None) -> Guardrails:
    """
    Initialize the global guardrails instance.
    
    Args:
        limits: Guardrail limits configuration
        
    Returns:
        Initialized guardrails instance
    """
    global _guardrails
    _guardrails = Guardrails(limits=limits)
    return _guardrails
