"""
OpenAI Provider

Uses the OpenAI Python SDK or plain HTTPS to interact with OpenAI API.
Supports function calling and streaming.
"""
import json
from typing import Optional, Iterator, Dict, List, Any
from .base import BaseProvider, ChatResponse, ToolCall

# Try to import OpenAI SDK
try:
    from openai import OpenAI
    _OPENAI_SDK_AVAILABLE = True
except ImportError:
    _OPENAI_SDK_AVAILABLE = False

# Fallback to requests for HTTP
try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


class OpenAIProvider(BaseProvider):
    """OpenAI API provider with function calling support."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout: int = 45,
        max_retries: int = 3,
        max_tokens: int = 1024,
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            max_tokens: Maximum tokens to generate
        """
        super().__init__(timeout, max_retries)
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        
        # Initialize SDK client if available
        if _OPENAI_SDK_AVAILABLE:
            self.client = OpenAI(api_key=api_key, timeout=timeout)
        else:
            self.client = None
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[Dict[str, Any]] = None,
        tool_choice: Optional[str] = None,
        stream: bool = False,
    ) -> ChatResponse | Iterator[str]:
        """
        Send a chat completion request to OpenAI.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional tool definitions (JSON schema format)
            tool_choice: Optional tool choice strategy
            stream: Whether to stream the response
            
        Returns:
            ChatResponse object if stream=False, Iterator[str] if stream=True
        """
        if self.client and _OPENAI_SDK_AVAILABLE:
            return self._chat_with_sdk(messages, tools, tool_choice, stream)
        elif _REQUESTS_AVAILABLE:
            return self._chat_with_requests(messages, tools, tool_choice, stream)
        else:
            raise RuntimeError(
                "Neither OpenAI SDK nor requests library is available. "
                "Please install: pip install openai"
            )
    
    def _chat_with_sdk(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[Dict[str, Any]],
        tool_choice: Optional[str],
        stream: bool,
    ) -> ChatResponse | Iterator[str]:
        """Use OpenAI SDK for chat completion."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Prepare request parameters
                params = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "stream": stream,
                }
                
                # Add tools if provided
                if tools:
                    params["tools"] = self._convert_tools_to_openai_format(tools)
                    if tool_choice:
                        params["tool_choice"] = tool_choice
                
                # Make request
                response = self.client.chat.completions.create(**params)
                
                if stream:
                    return self._handle_streaming_response(response)
                else:
                    return self._parse_response(response)
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1 and self._is_retryable_error(e):
                    self._wait_with_backoff(attempt)
                else:
                    break
        
        # All retries exhausted
        error_msg = self._normalize_error(last_error)
        raise RuntimeError(error_msg)
    
    def _chat_with_requests(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[Dict[str, Any]],
        tool_choice: Optional[str],
        stream: bool,
    ) -> ChatResponse | Iterator[str]:
        """Fallback to plain HTTPS using requests library."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Prepare request
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "stream": stream,
                }
                
                if tools:
                    payload["tools"] = self._convert_tools_to_openai_format(tools)
                    if tool_choice:
                        payload["tool_choice"] = tool_choice
                
                # Make request
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    stream=stream,
                )
                response.raise_for_status()
                
                if stream:
                    return self._handle_streaming_response_requests(response)
                else:
                    return self._parse_response_dict(response.json())
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1 and self._is_retryable_error(e):
                    self._wait_with_backoff(attempt)
                else:
                    break
        
        error_msg = self._normalize_error(last_error)
        raise RuntimeError(error_msg)
    
    def _convert_tools_to_openai_format(self, tools: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert tool definitions to OpenAI function calling format.
        
        Args:
            tools: Dictionary of tool definitions
            
        Returns:
            List of tool definitions in OpenAI format
        """
        openai_tools = []
        
        # tools can be a dict of tool_name -> schema
        if isinstance(tools, dict):
            for tool_name, tool_def in tools.items():
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_def.get("description", ""),
                        "parameters": tool_def.get("parameters", {}),
                    }
                }
                openai_tools.append(openai_tool)
        # Or a list of tool definitions already in OpenAI format
        elif isinstance(tools, list):
            openai_tools = tools
        
        return openai_tools
    
    def _parse_response(self, response) -> ChatResponse:
        """Parse OpenAI SDK response."""
        choice = response.choices[0]
        message = choice.message
        
        # Extract content
        content = message.content or ""
        
        # Extract tool calls
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )
        
        # Extract usage
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        
        return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)
    
    def _parse_response_dict(self, response_data: dict) -> ChatResponse:
        """Parse response from requests library."""
        choice = response_data["choices"][0]
        message = choice["message"]
        
        # Extract content
        content = message.get("content", "")
        
        # Extract tool calls
        tool_calls = []
        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                tool_calls.append(
                    ToolCall(
                        name=tc["function"]["name"],
                        arguments=json.loads(tc["function"]["arguments"]),
                    )
                )
        
        # Extract usage
        usage = {
            "input_tokens": response_data["usage"]["prompt_tokens"],
            "output_tokens": response_data["usage"]["completion_tokens"],
        }
        
        return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)
    
    def _handle_streaming_response(self, response) -> Iterator[str]:
        """Handle streaming response from OpenAI SDK."""
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content
    
    def _handle_streaming_response_requests(self, response) -> Iterator[str]:
        """Handle streaming response from requests library."""
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue
