"""
DAW Agent with Tool Execution

Agent loop that:
1. Sends user queries to LLM with tool schemas
2. Previews tool calls before execution (dry-run mode)
3. Executes tool calls via IPC client with safeguards
4. Returns results and summaries
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging
import sys
from ..ai.providers.base import BaseProvider, ChatResponse
from ..ipc.client import IPCClient
from ..ai.guardrails import get_guardrails, safe_format_exception
from ..telemetry import get_telemetry

logger = logging.getLogger(__name__)


@dataclass
class ToolCallAction:
    """Represents a single tool call action in a plan."""
    tool_name: str
    arguments: Dict[str, Any]
    description: str  # Human-readable description
    checked: bool = True  # For UI checkbox
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AgentPlan:
    """Represents an agent execution plan."""
    actions: List[ToolCallAction]
    reasoning: str  # LLM's explanation
    raw_response: ChatResponse


class AgentError(Exception):
    """Exception raised for agent errors."""
    pass


def _is_destructive_action(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if an action is potentially destructive.
    
    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        
    Returns:
        Tuple of (is_destructive, reason)
    """
    # Use guardrails to check for destructive patterns
    guardrails = get_guardrails()
    return guardrails.check_destructive_patterns(tool_name, arguments)


def _validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
    """
    Validate tool arguments and clamp values.
    
    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        
    Returns:
        Error message if validation fails, None otherwise
    """
    guardrails = get_guardrails()
    
    # Validate set_param
    if tool_name == "set_param":
        if "value01" in arguments:
            value = arguments["value01"]
            if not isinstance(value, (int, float)):
                return f"value01 must be a number, got {type(value)}"
            if value < 0.0 or value > 1.0:
                return f"value01 must be in range 0.0-1.0, got {value}"
        
        if "index" in arguments:
            if not isinstance(arguments["index"], int) or arguments["index"] < 0:
                return f"Parameter index must be a non-negative integer"
            
            # Use guardrails validation
            if "value01" in arguments:
                error = guardrails.validate_parameter(arguments["index"], arguments["value01"])
                if error:
                    return error
    
    # Validate set_note_batch
    elif tool_name == "set_note_batch":
        if "notes" not in arguments:
            return "set_note_batch requires 'notes' argument"
        
        notes = arguments["notes"]
        if not isinstance(notes, list):
            return "notes must be a list"
        
        # Use guardrails validation for note count and ranges
        error = guardrails.validate_notes(notes)
        if error:
            return error
        
        for i, note in enumerate(notes):
            if not isinstance(note, dict):
                return f"Note {i} must be a dict"
            
            # Check required fields
            required = ["pitch", "start", "duration", "velocity"]
            for field in required:
                if field not in note:
                    return f"Note {i} missing required field: {field}"
            
            # Type validation
            pitch = note["pitch"]
            if not isinstance(pitch, int):
                return f"Note {i} pitch must be an integer, got {type(pitch)}"
            
            velocity = note["velocity"]
            if not isinstance(velocity, int):
                return f"Note {i} velocity must be an integer, got {type(velocity)}"
            
            duration = note["duration"]
            if not isinstance(duration, (int, float)):
                return f"Note {i} duration must be a number, got {type(duration)}"
            
            start = note["start"]
            if not isinstance(start, (int, float)):
                return f"Note {i} start must be a number, got {type(start)}"
    
    # Validate transport
    elif tool_name == "transport":
        if "cmd" not in arguments:
            return "transport requires 'cmd' argument"
        
        valid_cmds = [
            "play", "stop", "record", "pause", "rewind",
            "fast_forward", "loop_toggle", "metronome_toggle"
        ]
        if arguments["cmd"] not in valid_cmds:
            return f"Invalid transport command: {arguments['cmd']}"
    
    # Validate mixer
    elif tool_name == "mixer":
        if "action" not in arguments:
            return "mixer requires 'action' argument"
        if "track" not in arguments:
            return "mixer requires 'track' argument"
        if "value" not in arguments:
            return "mixer requires 'value' argument"
        
        valid_actions = ["set_volume", "set_pan"]
        if arguments["action"] not in valid_actions:
            return f"Invalid mixer action: {arguments['action']}"
    
    return None


def _describe_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Generate human-readable description of a tool call.
    
    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        
    Returns:
        Human-readable description
    """
    if tool_name == "list_state":
        return "Get current FL Studio state (channels, plugins, mixer)"
    
    elif tool_name == "get_params":
        plugin_ref = arguments.get("plugin_ref", "?")
        return f"Get parameters for plugin {plugin_ref}"
    
    elif tool_name == "set_param":
        plugin_ref = arguments.get("plugin_ref", "?")
        index = arguments.get("index", "?")
        value = arguments.get("value01", "?")
        return f"Set plugin {plugin_ref} parameter {index} to {value:.3f}"
    
    elif tool_name == "set_note_batch":
        channel_ref = arguments.get("channel_ref", "?")
        notes = arguments.get("notes", [])
        return f"Add {len(notes)} notes to channel {channel_ref}"
    
    elif tool_name == "transport":
        cmd = arguments.get("cmd", "?")
        return f"Transport: {cmd}"
    
    elif tool_name == "mixer":
        action = arguments.get("action", "?")
        track = arguments.get("track", "?")
        value = arguments.get("value", "?")
        return f"Mixer track {track}: {action} = {value}"
    
    elif tool_name == "channel":
        index = arguments.get("select_index", "?")
        return f"Select channel {index}"
    
    else:
        return f"Unknown tool: {tool_name}"


def run_agent(
    query: str,
    provider: BaseProvider,
    tools: Dict[str, Dict[str, Any]],
    ipc_client: Optional[IPCClient] = None,
    max_steps: int = 8,
    dry_run: bool = True,
    system_prompt: Optional[str] = None,
) -> AgentPlan:
    """
    Run the DAW agent with a user query.
    
    Args:
        query: User's natural language query
        provider: AI provider (OpenAI, Ollama, etc.)
        tools: Tool schemas dict from get_tool_schemas()
        ipc_client: IPC client for executing tools (required if dry_run=False)
        max_steps: Maximum number of agent steps/tool calls
        dry_run: If True, only preview actions without executing
        system_prompt: Optional system prompt override
        
    Returns:
        AgentPlan with actions and results
        
    Raises:
        AgentError: If agent execution fails
    """
    if not dry_run and ipc_client is None:
        raise AgentError("ipc_client is required when dry_run=False")
    
    # Get guardrails and telemetry instances
    guardrails = get_guardrails()
    telemetry = get_telemetry()
    
    # Reset per-query execution counter
    guardrails.reset_query()
    
    # Log query to telemetry
    provider_name = getattr(provider, '__class__', 'unknown').__name__
    telemetry.log_agent_query(query, provider_name, dry_run)
    
    # Default system prompt
    if system_prompt is None:
        system_prompt = """You are an intelligent DAW assistant for FL Studio.
Use the provided tools to help the user. Always call tools to interact with FL Studio.
Be precise and verify your actions."""
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    
    # Convert tools to function call format
    functions = []
    for tool_name, tool_schema in tools.items():
        functions.append({
            "name": tool_name,
            "description": tool_schema["description"],
            "parameters": tool_schema["parameters"],
        })
    
    # Call provider
    try:
        response = provider.chat(
            messages=messages,
            tools=functions,
            tool_choice="auto",
            stream=False,
        )
    except Exception as e:
        # Log error with safe formatting (redact secrets)
        safe_error = safe_format_exception(e)
        logger.error(f"Provider error: {safe_error}")
        telemetry.log_error("provider_error", safe_error)
        raise AgentError(f"Provider error: {safe_error}")
    
    # Check if we got tool calls
    if not response.tool_calls:
        # No tool calls, just return the text response
        return AgentPlan(
            actions=[],
            reasoning=response.content or "No actions needed.",
            raw_response=response,
        )
    
    # Limit number of tool calls
    if len(response.tool_calls) > max_steps:
        raise AgentError(
            f"Too many tool calls ({len(response.tool_calls)}), maximum is {max_steps}"
        )
    
    # Build action plan
    actions = []
    for tool_call in response.tool_calls:
        tool_name = tool_call.name
        arguments = tool_call.arguments
        
        # Check if tool exists
        if tool_name not in tools:
            raise AgentError(f"Unknown tool: {tool_name}")
        
        # Validate arguments
        error = _validate_tool_arguments(tool_name, arguments)
        if error:
            raise AgentError(f"Invalid arguments for {tool_name}: {error}")
        
        # Check for destructive actions
        is_destructive, reason = _is_destructive_action(tool_name, arguments)
        if is_destructive:
            raise AgentError(f"Destructive action blocked: {reason}")
        
        # Create action
        action = ToolCallAction(
            tool_name=tool_name,
            arguments=arguments,
            description=_describe_tool_call(tool_name, arguments),
            checked=True,
        )
        actions.append(action)
    
    # If dry_run, return plan without executing
    if dry_run:
        return AgentPlan(
            actions=actions,
            reasoning=response.content or "Proposed actions:",
            raw_response=response,
        )
    
    # Execute actions
    for action in actions:
        if not action.checked:
            # Skip unchecked actions
            continue
        
        # Check rate limit before execution
        rate_error = guardrails.check_rate_limit()
        if rate_error:
            action.error = rate_error
            telemetry.log_error("rate_limit", rate_error)
            logger.warning(f"Rate limit exceeded for {action.tool_name}")
            continue
        
        try:
            # Execute tool via IPC client
            if action.tool_name == "list_state":
                result = ipc_client.list_state()
            elif action.tool_name == "get_params":
                result = ipc_client.get_params(action.arguments["plugin_ref"])
            elif action.tool_name == "set_param":
                result = ipc_client.set_param(
                    action.arguments["plugin_ref"],
                    action.arguments["index"],
                    action.arguments["value01"],
                )
            elif action.tool_name == "set_note_batch":
                result = ipc_client.set_note_batch(
                    action.arguments["channel_ref"],
                    action.arguments["notes"],
                )
            elif action.tool_name == "transport":
                result = ipc_client.transport(action.arguments["cmd"])
            elif action.tool_name == "mixer":
                result = ipc_client.mixer(
                    action.arguments["action"],
                    action.arguments["track"],
                    action.arguments["value"],
                )
            elif action.tool_name == "channel":
                result = ipc_client.channel(action.arguments["select_index"])
            else:
                raise AgentError(f"Unknown tool: {action.tool_name}")
            
            action.result = result
            telemetry.log_tool_execution(action.tool_name, True)
            
        except Exception as e:
            # Redact secrets from error message
            safe_error = safe_format_exception(e)
            action.error = safe_error
            telemetry.log_tool_execution(action.tool_name, False, safe_error)
            logger.error(f"Tool execution failed for {action.tool_name}: {safe_error}")
    
    return AgentPlan(
        actions=actions,
        reasoning=response.content or "Actions executed:",
        raw_response=response,
    )


def _provider_check() -> int:
    """
    CLI command to check which AI provider is configured.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        from .config import get_config
        
        config = get_config()
        provider, error = config.resolve_provider()
        
        print("=" * 60)
        print("FL-AI-Producer Provider Check")
        print("=" * 60)
        print()
        
        if error:
            print(f"❌ Provider Configuration Error:")
            print(f"   {error}")
            print()
            print("Available options:")
            print("  • Set OPENAI_API_KEY environment variable or .env file")
            print("  • Install and run Ollama: https://ollama.ai")
            print("  • Set AI_PROVIDER=auto|openai|ollama")
            return 1
        
        print(f"✓ Provider: {provider}")
        print()
        
        if provider == "openai":
            print(f"  Model: {config.openai_model}")
            print(f"  API Key: {'*' * 8}{config.openai_api_key[-4:] if config.openai_api_key else 'NOT SET'}")
        elif provider == "ollama":
            print(f"  Host: {config.ollama_host}")
            print(f"  Model: {config.ollama_model}")
        
        print()
        print(f"  Request Timeout: {config.request_timeout_sec}s")
        print(f"  Max Tokens: {config.max_tokens}")
        print()
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"Error checking provider: {e}", file=sys.stderr)
        return 1


def _selftest() -> int:
    """
    CLI command to run basic self-tests of the agent.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        from .templates.tool_schemas import get_tool_schemas
        from .providers.base import ChatResponse, ToolCall
        
        print("=" * 60)
        print("FL-AI-Producer Self-Test")
        print("=" * 60)
        print()
        
        # Test 1: Load tool schemas
        print("✓ Test 1: Loading tool schemas...")
        tools = get_tool_schemas()
        print(f"  Loaded {len(tools)} tools: {', '.join(tools.keys())}")
        print()
        
        # Test 2: Create a mock provider and test agent dry-run
        print("✓ Test 2: Testing agent dry-run mode...")
        
        class MockProvider:
            """Mock provider for testing."""
            def chat(self, messages, tools=None, tool_choice=None, stream=False):
                return ChatResponse(
                    content="Setting parameter value",
                    tool_calls=[
                        ToolCall(
                            name="set_param",
                            arguments={
                                "plugin_ref": "0:0",
                                "index": 0,
                                "value01": 0.5,
                            }
                        )
                    ],
                    usage={"input_tokens": 10, "output_tokens": 5},
                )
        
        provider = MockProvider()
        plan = run_agent(
            query="Set parameter 0 to 0.5",
            provider=provider,
            tools=tools,
            dry_run=True,
        )
        
        print(f"  Agent generated {len(plan.actions)} actions")
        for i, action in enumerate(plan.actions, 1):
            print(f"    {i}. {action.description}")
        print()
        
        # Test 3: Validate tool argument validation
        print("✓ Test 3: Testing tool argument validation...")
        error = _validate_tool_arguments("set_param", {
            "plugin_ref": "0:0",
            "index": 0,
            "value01": 0.5,
        })
        if error:
            print(f"  Unexpected validation error: {error}")
            return 1
        print("  Argument validation passed")
        print()
        
        # Test 4: Check guardrails
        print("✓ Test 4: Testing guardrails...")
        guardrails = get_guardrails()
        guardrails.reset_query()
        is_destructive, reason = guardrails.check_destructive_patterns("set_param", {
            "plugin_ref": "0:0",
            "index": 0,
            "value01": 0.5,
        })
        print(f"  Destructive check: {is_destructive} (reason: {reason or 'none'})")
        print()
        
        # Test 5: Provider check
        print("✓ Test 5: Checking provider configuration...")
        from .config import get_config
        config = get_config()
        provider_name, error = config.resolve_provider()
        if error:
            print(f"  ⚠ Warning: {error}")
            print("  Note: This is expected if no provider is configured")
        else:
            print(f"  Provider available: {provider_name}")
        print()
        
        print("=" * 60)
        print("✓ All self-tests passed!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"❌ Self-test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _cli_main():
    """CLI entry point for agent commands."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="FL-AI-Producer Agent CLI",
        prog="python -m controller_app.ai.agent"
    )
    parser.add_argument(
        "--provider-check",
        action="store_true",
        help="Check which AI provider is configured"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run basic self-tests of the agent"
    )
    
    args = parser.parse_args()
    
    if args.provider_check:
        return _provider_check()
    elif args.selftest:
        return _selftest()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(_cli_main())
