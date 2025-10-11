"""
Tests for AI Providers

Tests OpenAI and Ollama providers with mocked HTTP requests.
Tests retry logic, timeouts, and provider selection.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from controller_app.ai.config import AIConfig, get_config
from controller_app.ai.providers import (
    BaseProvider,
    ChatResponse,
    ToolCall,
    OpenAIProvider,
    OllamaProvider,
)


class TestAIConfig:
    """Tests for AI configuration."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = AIConfig()
        assert config.openai_model == "gpt-4o-mini"
        assert config.ollama_host == "http://127.0.0.1:11434"
        assert config.ollama_model == "llama3.1"
        assert config.ai_provider == "auto"
        assert config.request_timeout_sec == 45
        assert config.max_tokens == 1024
    
    def test_config_from_env(self, monkeypatch):
        """Test loading configuration from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:8080")
        monkeypatch.setenv("OLLAMA_MODEL", "codellama")
        monkeypatch.setenv("AI_PROVIDER", "openai")
        monkeypatch.setenv("REQUEST_TIMEOUT_SEC", "60")
        monkeypatch.setenv("MAX_TOKENS", "2048")
        
        config = AIConfig()
        assert config.openai_api_key == "test-key-123"
        assert config.openai_model == "gpt-4"
        assert config.ollama_host == "http://localhost:8080"
        assert config.ollama_model == "codellama"
        assert config.ai_provider == "openai"
        assert config.request_timeout_sec == 60
        assert config.max_tokens == 2048
    
    def test_resolve_provider_auto_with_key(self, monkeypatch):
        """Test auto provider selection with OpenAI key."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AI_PROVIDER", "auto")
        
        config = AIConfig()
        provider, error = config.resolve_provider()
        assert provider == "openai"
        assert error is None
    
    def test_resolve_provider_auto_without_key(self, monkeypatch):
        """Test auto provider selection without OpenAI key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("AI_PROVIDER", "auto")
        
        config = AIConfig()
        provider, error = config.resolve_provider()
        assert provider == "ollama"
        assert error is None
    
    def test_resolve_provider_openai_without_key(self, monkeypatch):
        """Test OpenAI provider selection without key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("AI_PROVIDER", "openai")
        
        config = AIConfig()
        provider, error = config.resolve_provider()
        assert provider == "openai"
        assert error is not None
        assert "OPENAI_API_KEY" in error
    
    def test_resolve_provider_ollama(self, monkeypatch):
        """Test Ollama provider selection."""
        monkeypatch.setenv("AI_PROVIDER", "ollama")
        
        config = AIConfig()
        provider, error = config.resolve_provider()
        assert provider == "ollama"
        assert error is None


class TestBaseProvider:
    """Tests for base provider functionality."""
    
    def test_wait_with_backoff(self):
        """Test exponential backoff."""
        provider = OpenAIProvider(api_key="test")
        
        # Mock time.sleep to avoid actual delays
        with patch("time.sleep") as mock_sleep:
            provider._wait_with_backoff(0, jitter=False)
            mock_sleep.assert_called_once()
            call_args = mock_sleep.call_args[0][0]
            assert call_args == 1.0  # Initial backoff
            
            mock_sleep.reset_mock()
            provider._wait_with_backoff(1, jitter=False)
            call_args = mock_sleep.call_args[0][0]
            assert call_args == 2.0  # 1.0 * 2^1
            
            mock_sleep.reset_mock()
            provider._wait_with_backoff(2, jitter=False)
            call_args = mock_sleep.call_args[0][0]
            assert call_args == 4.0  # 1.0 * 2^2
    
    def test_is_retryable_error(self):
        """Test retryable error detection."""
        provider = OpenAIProvider(api_key="test")
        
        assert provider._is_retryable_error(Exception("Connection timeout"))
        assert provider._is_retryable_error(Exception("429 rate limit"))
        assert provider._is_retryable_error(Exception("503 service unavailable"))
        assert not provider._is_retryable_error(Exception("Invalid API key"))
    
    def test_normalize_error(self):
        """Test error message normalization."""
        provider = OpenAIProvider(api_key="test")
        
        msg = provider._normalize_error(Exception("timeout"))
        assert "timed out" in msg.lower()
        
        msg = provider._normalize_error(Exception("429 rate limit"))
        assert "rate limit" in msg.lower()
        
        msg = provider._normalize_error(Exception("connection refused"))
        assert "connection" in msg.lower()


class TestOpenAIProvider:
    """Tests for OpenAI provider."""
    
    @patch("controller_app.ai.providers.openai_provider._OPENAI_SDK_AVAILABLE", False)
    @patch("controller_app.ai.providers.openai_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.openai_provider.requests")
    def test_chat_basic(self, mock_requests):
        """Test basic chat completion."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Hello, world!",
                    "role": "assistant"
                }
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5
            }
        }
        mock_requests.post.return_value = mock_response
        
        provider = OpenAIProvider(api_key="test-key")
        messages = [{"role": "user", "content": "Hello"}]
        
        response = provider.chat(messages)
        
        assert isinstance(response, ChatResponse)
        assert response.content == "Hello, world!"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 5
    
    @patch("controller_app.ai.providers.openai_provider._OPENAI_SDK_AVAILABLE", False)
    @patch("controller_app.ai.providers.openai_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.openai_provider.requests")
    def test_chat_with_tools(self, mock_requests):
        """Test chat with tool calls."""
        # Mock response with tool call
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "",
                    "role": "assistant",
                    "tool_calls": [{
                        "function": {
                            "name": "list_state",
                            "arguments": "{}"
                        }
                    }]
                }
            }],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 20
            }
        }
        mock_requests.post.return_value = mock_response
        
        provider = OpenAIProvider(api_key="test-key")
        messages = [{"role": "user", "content": "What's in my project?"}]
        tools = {
            "list_state": {
                "description": "Get project state",
                "parameters": {"type": "object", "properties": {}}
            }
        }
        
        response = provider.chat(messages, tools=tools)
        
        assert isinstance(response, ChatResponse)
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "list_state"
    
    @patch("controller_app.ai.providers.openai_provider._OPENAI_SDK_AVAILABLE", False)
    @patch("controller_app.ai.providers.openai_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.openai_provider.requests")
    def test_chat_retry_on_429(self, mock_requests):
        """Test retry on rate limit (429)."""
        # First call fails with 429, second succeeds
        fail_response = Mock()
        fail_response.raise_for_status.side_effect = Exception("429 rate limit")
        
        success_response = Mock()
        success_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Success after retry",
                    "role": "assistant"
                }
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        
        mock_requests.post.side_effect = [fail_response, success_response]
        
        provider = OpenAIProvider(api_key="test-key", max_retries=2)
        messages = [{"role": "user", "content": "Test"}]
        
        with patch("time.sleep"):  # Mock sleep to avoid delays
            response = provider.chat(messages)
        
        assert response.content == "Success after retry"
        assert mock_requests.post.call_count == 2
    
    @patch("controller_app.ai.providers.openai_provider._OPENAI_SDK_AVAILABLE", False)
    @patch("controller_app.ai.providers.openai_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.openai_provider.requests")
    def test_chat_timeout(self, mock_requests):
        """Test timeout handling."""
        mock_requests.post.side_effect = Exception("timeout")
        
        provider = OpenAIProvider(api_key="test-key", max_retries=1, timeout=1)
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.chat(messages)
        
        assert "timed out" in str(exc_info.value).lower()
    
    @patch("controller_app.ai.providers.openai_provider._OPENAI_SDK_AVAILABLE", False)
    @patch("controller_app.ai.providers.openai_provider._REQUESTS_AVAILABLE", False)
    def test_chat_no_requests_library(self):
        """Test error when no HTTP library is available."""
        provider = OpenAIProvider(api_key="test-key")
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.chat(messages)
        
        assert "OpenAI SDK" in str(exc_info.value) or "requests" in str(exc_info.value)


class TestOllamaProvider:
    """Tests for Ollama provider."""
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_chat_basic(self, mock_requests):
        """Test basic chat completion."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {
                "content": "Hello from Ollama!",
                "role": "assistant"
            },
            "prompt_eval_count": 15,
            "eval_count": 8
        }
        mock_requests.post.return_value = mock_response
        
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]
        
        response = provider.chat(messages)
        
        assert isinstance(response, ChatResponse)
        assert response.content == "Hello from Ollama!"
        assert response.usage["input_tokens"] == 15
        assert response.usage["output_tokens"] == 8
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_chat_with_tools_json_response(self, mock_requests):
        """Test tool calls via JSON compatibility layer."""
        # Mock response with tool call in JSON format
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {
                "content": json.dumps({
                    "tool_calls": [{
                        "name": "transport",
                        "arguments": {"cmd": "play"}
                    }]
                }),
                "role": "assistant"
            },
            "prompt_eval_count": 50,
            "eval_count": 30
        }
        mock_requests.post.return_value = mock_response
        
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Start playing"}]
        tools = {
            "transport": {
                "description": "Control transport",
                "parameters": {"type": "object"}
            }
        }
        
        response = provider.chat(messages, tools=tools)
        
        assert isinstance(response, ChatResponse)
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "transport"
        assert response.tool_calls[0].arguments["cmd"] == "play"
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_chat_retry_on_connection_error(self, mock_requests):
        """Test retry on connection error."""
        # First call fails, second succeeds
        fail_response = Mock()
        fail_response.raise_for_status.side_effect = Exception("connection timeout")
        
        success_response = Mock()
        success_response.json.return_value = {
            "message": {
                "content": "Success after retry",
                "role": "assistant"
            },
            "prompt_eval_count": 10,
            "eval_count": 5
        }
        
        mock_requests.post.side_effect = [fail_response, success_response]
        
        provider = OllamaProvider(max_retries=2)
        messages = [{"role": "user", "content": "Test"}]
        
        with patch("time.sleep"):  # Mock sleep
            response = provider.chat(messages)
        
        assert response.content == "Success after retry"
        assert mock_requests.post.call_count == 2
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", False)
    def test_chat_no_requests_library(self):
        """Test error when requests library is not available."""
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.chat(messages)
        
        assert "requests" in str(exc_info.value).lower()
    
    def test_inject_tool_instructions(self):
        """Test tool instructions injection."""
        provider = OllamaProvider()
        messages = [
            {"role": "user", "content": "Do something"}
        ]
        tools = {
            "test_tool": {
                "description": "A test tool",
                "parameters": {"type": "object"}
            }
        }
        
        modified = provider._inject_tool_instructions(messages, tools)
        
        # Should have system message added
        assert len(modified) == 2
        assert modified[0]["role"] == "system"
        assert "test_tool" in modified[0]["content"]
        assert modified[1] == messages[0]


class TestToolSchemas:
    """Tests for tool schemas."""
    
    def test_get_tool_schemas(self):
        """Test getting all tool schemas."""
        from controller_app.ai.templates.tool_schemas import get_tool_schemas
        
        schemas = get_tool_schemas()
        
        # Check all expected tools are present
        expected_tools = [
            "list_state", "get_params", "set_param", "set_note_batch",
            "transport", "mixer", "channel"
        ]
        for tool in expected_tools:
            assert tool in schemas
            assert "description" in schemas[tool]
            assert "parameters" in schemas[tool]
    
    def test_tool_schema_structure(self):
        """Test tool schema structure."""
        from controller_app.ai.templates.tool_schemas import get_tool_schemas
        
        schemas = get_tool_schemas()
        
        # Test set_param schema in detail
        set_param = schemas["set_param"]
        assert "plugin_ref" in set_param["parameters"]["properties"]
        assert "index" in set_param["parameters"]["properties"]
        assert "value01" in set_param["parameters"]["properties"]
        assert set_param["parameters"]["required"] == ["plugin_ref", "index", "value01"]
    
    def test_get_tool_callable(self):
        """Test getting tool callables."""
        from controller_app.ai.templates.tool_schemas import get_tool_callable
        
        callable_fn = get_tool_callable("list_state")
        assert callable_fn is not None
        assert callable(callable_fn)
        
        # Should raise NotImplementedError for now
        with pytest.raises(NotImplementedError):
            callable_fn()
        
        # Non-existent tool should return None
        assert get_tool_callable("nonexistent") is None


class TestSystemPrompts:
    """Tests for system prompts."""
    
    def test_get_daw_agent_system_prompt(self):
        """Test DAW agent system prompt."""
        from controller_app.ai.templates.system_prompts import get_daw_agent_system_prompt
        
        prompt = get_daw_agent_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "DAW" in prompt or "FL Studio" in prompt
        assert "tool" in prompt.lower()
        
        # Check for key instructions
        assert "list_state" in prompt
        assert "get_params" in prompt
        assert "0.0 to 1.0" in prompt or "0-1" in prompt


class TestChatResponse:
    """Tests for ChatResponse data structure."""
    
    def test_chat_response_creation(self):
        """Test creating ChatResponse."""
        response = ChatResponse(
            content="Test content",
            tool_calls=[],
            usage={"input_tokens": 10, "output_tokens": 5}
        )
        
        assert response.content == "Test content"
        assert response.tool_calls == []
        assert response.usage["input_tokens"] == 10
    
    def test_chat_response_to_dict(self):
        """Test converting ChatResponse to dict."""
        response = ChatResponse(
            content="Test",
            tool_calls=[
                ToolCall(name="test_tool", arguments={"arg": "value"})
            ],
            usage={"input_tokens": 10, "output_tokens": 5}
        )
        
        result = response.to_dict()
        
        assert result["content"] == "Test"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "test_tool"
        assert result["tool_calls"][0]["arguments"]["arg"] == "value"
        assert result["usage"]["input_tokens"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
