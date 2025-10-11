"""
Base Provider Abstract Class

Defines the interface for AI providers with standardized response format,
retry logic, and error handling.
"""
from abc import ABC, abstractmethod
from typing import Optional, Iterator, Dict, List, Any
from dataclasses import dataclass
import time
import random


@dataclass
class ToolCall:
    """Represents a tool/function call from the model."""
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    """Standardized response from chat completion."""
    content: str
    tool_calls: List[ToolCall]
    usage: Dict[str, int]  # {"input_tokens": int, "output_tokens": int}
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "content": self.content,
            "tool_calls": [
                {"name": tc.name, "arguments": tc.arguments}
                for tc in self.tool_calls
            ],
            "usage": self.usage,
        }


class BaseProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, timeout: int = 45, max_retries: int = 3):
        """
        Initialize the provider.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = 1.0  # seconds
        self.max_backoff = 30.0  # seconds
        self.backoff_multiplier = 2.0
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[Dict[str, Any]] = None,
        tool_choice: Optional[str] = None,
        stream: bool = False,
    ) -> ChatResponse | Iterator[str]:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional tool definitions (JSON schema format)
            tool_choice: Optional tool choice strategy ("auto", "none", or specific tool)
            stream: Whether to stream the response
            
        Returns:
            ChatResponse object if stream=False, Iterator[str] if stream=True
            
        Raises:
            TimeoutError: If request times out
            RuntimeError: For other errors after retries exhausted
        """
        pass
    
    def _wait_with_backoff(self, attempt: int, jitter: bool = True) -> None:
        """
        Wait with exponential backoff.
        
        Args:
            attempt: Current retry attempt number (0-indexed)
            jitter: Whether to add random jitter
        """
        backoff = min(
            self.initial_backoff * (self.backoff_multiplier ** attempt),
            self.max_backoff
        )
        
        if jitter:
            # Add random jitter (±20%)
            jitter_amount = backoff * 0.2
            backoff += random.uniform(-jitter_amount, jitter_amount)
        
        time.sleep(backoff)
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the error should be retried
        """
        # Retry on connection errors, timeouts, and rate limits
        error_str = str(error).lower()
        retryable_patterns = [
            "timeout",
            "connection",
            "429",
            "rate limit",
            "too many requests",
            "503",
            "service unavailable",
            "502",
            "bad gateway",
        ]
        return any(pattern in error_str for pattern in retryable_patterns)
    
    def _normalize_error(self, error: Exception) -> str:
        """
        Normalize error messages for consistent handling.
        
        Args:
            error: The exception to normalize
            
        Returns:
            Normalized error message
        """
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return f"Request timed out after {self.timeout} seconds"
        elif "429" in error_str or "rate limit" in error_str:
            return "Rate limit exceeded, please try again later"
        elif "connection" in error_str:
            return "Connection error, please check network connectivity"
        elif "authentication" in error_str or "api key" in error_str:
            return "Authentication failed, please check API key"
        else:
            return f"Request failed: {str(error)}"
