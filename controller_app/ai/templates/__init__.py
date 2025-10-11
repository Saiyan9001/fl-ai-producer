"""
AI Templates Module

System prompts and tool schemas for the DAW agent.
"""
from .system_prompts import get_daw_agent_system_prompt
from .tool_schemas import get_tool_schemas, get_tool_callable

__all__ = [
    "get_daw_agent_system_prompt",
    "get_tool_schemas",
    "get_tool_callable",
]
