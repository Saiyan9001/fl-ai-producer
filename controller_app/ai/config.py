"""
AI Provider Configuration

Loads configuration from environment variables or .env file.
Provides runtime configuration and provider selection logic.
"""
import os
from typing import Optional, Literal
from pathlib import Path

# Try to load python-dotenv if available
try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False


class AIConfig:
    """Configuration for AI providers."""
    
    def __init__(self):
        """Initialize configuration from environment."""
        # Load .env file if it exists and dotenv is available
        if _DOTENV_AVAILABLE:
            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        
        # OpenAI configuration
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Ollama configuration
        self.ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
        
        # Provider selection
        self.ai_provider: Literal["openai", "ollama", "auto"] = os.getenv(
            "AI_PROVIDER", "auto"
        )
        
        # Request configuration
        self.request_timeout_sec: int = int(os.getenv("REQUEST_TIMEOUT_SEC", "45"))
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "1024"))
    
    def resolve_provider(self) -> tuple[Literal["openai", "ollama"], Optional[str]]:
        """
        Resolve which provider to use based on configuration.
        
        Returns:
            Tuple of (provider_name, error_message)
            error_message is None if provider is available
        """
        if self.ai_provider == "openai":
            if self.openai_api_key:
                return ("openai", None)
            return ("openai", "OpenAI provider selected but OPENAI_API_KEY is not set")
        
        elif self.ai_provider == "ollama":
            return ("ollama", None)
        
        else:  # auto
            # Prefer OpenAI if key is available
            if self.openai_api_key:
                return ("openai", None)
            # Fall back to Ollama
            return ("ollama", None)
    
    def get_error_if_no_provider(self) -> Optional[str]:
        """
        Check if any provider is available.
        
        Returns:
            Error message if no provider is available, None otherwise
        """
        provider, error = self.resolve_provider()
        if error:
            return error
        return None


# Global configuration instance
config = AIConfig()


def get_config() -> AIConfig:
    """Get the global configuration instance."""
    return config
