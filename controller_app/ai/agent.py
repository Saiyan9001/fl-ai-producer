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
from ..ai.providers.base import BaseProvider, ChatResponse
from ..ipc.client import IPCClient


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
    # Check for ambiguous or destructive patterns
    destructive_patterns = [
        ("set_param", "reset all", "Resetting all parameters is destructive"),
        ("set_note_batch", "clear", "Clearing all notes is destructive"),
    ]
    
    for pattern_tool, pattern_key, reason in destructive_patterns:
        if tool_name == pattern_tool:
            # Check if any argument contains destructive keywords
            for key, value in arguments.items():
                if isinstance(value, str) and pattern_key in value.lower():
                    return True, reason
    
    return False, ""


def _validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
    """
    Validate tool arguments and clamp values.
    
    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        
    Returns:
        Error message if validation fails, None otherwise
    """
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
    
    # Validate set_note_batch
    elif tool_name == "set_note_batch":
        if "notes" not in arguments:
            return "set_note_batch requires 'notes' argument"
        
        notes = arguments["notes"]
        if not isinstance(notes, list):
            return "notes must be a list"
        
        for i, note in enumerate(notes):
            if not isinstance(note, dict):
                return f"Note {i} must be a dict"
            
            # Check required fields
            required = ["pitch", "start", "duration", "velocity"]
            for field in required:
                if field not in note:
                    return f"Note {i} missing required field: {field}"
            
            # Validate ranges
            pitch = note["pitch"]
            if not isinstance(pitch, int) or pitch < 0 or pitch > 127:
                return f"Note {i} pitch must be 0-127, got {pitch}"
            
            velocity = note["velocity"]
            if not isinstance(velocity, int) or velocity < 1 or velocity > 127:
                return f"Note {i} velocity must be 1-127, got {velocity}"
            
            duration = note["duration"]
            if not isinstance(duration, (int, float)) or duration <= 0:
                return f"Note {i} duration must be positive, got {duration}"
            
            start = note["start"]
            if not isinstance(start, (int, float)) or start < 0:
                return f"Note {i} start must be non-negative, got {start}"
    
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
        raise AgentError(f"Provider error: {e}")
    
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
            
        except Exception as e:
            action.error = str(e)
    
    return AgentPlan(
        actions=actions,
        reasoning=response.content or "Actions executed:",
        raw_response=response,
    )
