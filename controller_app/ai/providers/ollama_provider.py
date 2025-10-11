"""
Ollama Provider

Uses local Ollama REST API for chat completions.
Includes compatibility layer for tool calling.
"""
import json
from typing import Optional, Iterator, Dict, List, Any
from .base import BaseProvider, ChatResponse, ToolCall

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


class OllamaProvider(BaseProvider):
    """Ollama local API provider with tool calling compatibility."""
    
    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "llama3.1",
        timeout: int = 45,
        max_retries: int = 3,
        max_tokens: int = 1024,
    ):
        """
        Initialize Ollama provider.
        
        Args:
            host: Ollama host URL
            model: Model to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            max_tokens: Maximum tokens to generate
        """
        super().__init__(timeout, max_retries)
        self.host = host.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[Dict[str, Any]] = None,
        tool_choice: Optional[str] = None,
        stream: bool = False,
    ) -> ChatResponse | Iterator[str]:
        """
        Send a chat completion request to Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional tool definitions (JSON schema format)
            tool_choice: Optional tool choice strategy (not used in Ollama)
            stream: Whether to stream the response
            
        Returns:
            ChatResponse object if stream=False, Iterator[str] if stream=True
        """
        if not _REQUESTS_AVAILABLE:
            raise RuntimeError(
                "requests library is not available. Please install: pip install requests"
            )
        
        # Add tool instructions to system message if tools are provided
        if tools:
            messages = self._inject_tool_instructions(messages, tools)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                url = f"{self.host}/api/chat"
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": stream,
                    "options": {
                        "num_predict": self.max_tokens,
                    }
                }
                
                # Ollama supports tools natively in some models
                # Try to include them in the request
                if tools:
                    # Convert to Ollama-compatible format if possible
                    ollama_tools = self._convert_tools_to_ollama_format(tools)
                    if ollama_tools:
                        payload["tools"] = ollama_tools
                
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    stream=stream,
                )
                response.raise_for_status()
                
                if stream:
                    return self._handle_streaming_response(response)
                else:
                    return self._parse_response(response.json(), tools)
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1 and self._is_retryable_error(e):
                    self._wait_with_backoff(attempt)
                else:
                    break
        
        error_msg = self._normalize_error(last_error)
        raise RuntimeError(error_msg)
    
    def _inject_tool_instructions(
        self, messages: List[Dict[str, str]], tools: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Inject tool definitions into system message for models without native tool support.
        
        Args:
            messages: Original messages
            tools: Tool definitions
            
        Returns:
            Modified messages with tool instructions
        """
        # Build tool description
        tool_desc = "\n\nYou have access to the following tools:\n"
        for tool_name, tool_def in (tools.items() if isinstance(tools, dict) else []):
            tool_desc += f"\n- {tool_name}: {tool_def.get('description', 'No description')}\n"
            tool_desc += f"  Parameters: {json.dumps(tool_def.get('parameters', {}), indent=2)}\n"
        
        tool_desc += (
            "\nWhen you want to call a tool, respond with JSON in this format:\n"
            '{"tool_calls": [{"name": "tool_name", "arguments": {...}}]}\n'
            "Otherwise, respond normally with text."
        )
        
        # Add to system message or create one
        new_messages = []
        system_found = False
        
        for msg in messages:
            if msg["role"] == "system":
                # Append to existing system message
                new_msg = msg.copy()
                new_msg["content"] = msg["content"] + tool_desc
                new_messages.append(new_msg)
                system_found = True
            else:
                new_messages.append(msg)
        
        # If no system message, add one at the beginning
        if not system_found:
            new_messages.insert(0, {"role": "system", "content": tool_desc})
        
        return new_messages
    
    def _convert_tools_to_ollama_format(self, tools: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert tool definitions to Ollama format (if supported).
        
        Args:
            tools: Dictionary of tool definitions
            
        Returns:
            List of tool definitions in Ollama format
        """
        ollama_tools = []
        
        if isinstance(tools, dict):
            for tool_name, tool_def in tools.items():
                ollama_tool = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_def.get("description", ""),
                        "parameters": tool_def.get("parameters", {}),
                    }
                }
                ollama_tools.append(ollama_tool)
        elif isinstance(tools, list):
            ollama_tools = tools
        
        return ollama_tools
    
    def _parse_response(self, response_data: dict, tools: Optional[Dict[str, Any]]) -> ChatResponse:
        """
        Parse Ollama response.
        
        Args:
            response_data: Response from Ollama API
            tools: Tool definitions (for parsing tool calls)
            
        Returns:
            ChatResponse object
        """
        message = response_data.get("message", {})
        content = message.get("content", "")
        
        # Extract tool calls if present
        tool_calls = []
        
        # Check for native tool calls (if Ollama supports them)
        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                if "function" in tc:
                    tool_calls.append(
                        ToolCall(
                            name=tc["function"]["name"],
                            arguments=tc["function"].get("arguments", {}),
                        )
                    )
        
        # Check for tool calls in content (compatibility layer)
        elif tools and content.strip().startswith("{"):
            try:
                parsed = json.loads(content)
                if "tool_calls" in parsed and isinstance(parsed["tool_calls"], list):
                    for tc in parsed["tool_calls"]:
                        tool_calls.append(
                            ToolCall(
                                name=tc.get("name", ""),
                                arguments=tc.get("arguments", {}),
                            )
                        )
                    # Clear content since it was a tool call
                    content = ""
            except json.JSONDecodeError:
                # Not valid JSON, treat as regular content
                pass
        
        # Extract usage (Ollama provides this in different format)
        usage = {
            "input_tokens": response_data.get("prompt_eval_count", 0),
            "output_tokens": response_data.get("eval_count", 0),
        }
        
        return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)
    
    def _handle_streaming_response(self, response) -> Iterator[str]:
        """
        Handle streaming response from Ollama.
        
        Args:
            response: Streaming response object
            
        Yields:
            Text chunks
        """
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    if "message" in data:
                        content = data["message"].get("content", "")
                        if content:
                            yield content
                    
                    # Check if done
                    if data.get("done", False):
                        break
                        
                except json.JSONDecodeError:
                    continue
