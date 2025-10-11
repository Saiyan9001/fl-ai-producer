"""
Tool Schemas for FL Studio IPC

Defines JSON schemas for all available tools that map to IPC routes.
Each tool corresponds to a specific FL Studio operation.
"""
from typing import Dict, Any, Callable, Optional


def get_tool_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Get all tool schemas in a format compatible with LLM function calling.
    
    Returns:
        Dictionary mapping tool names to their definitions
    """
    return {
        "list_state": {
            "description": (
                "Get the current state of FL Studio including all channels, "
                "plugins, mixer tracks, and project info. Use this to understand "
                "what's in the project before making changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        
        "get_params": {
            "description": (
                "Get all parameters for a specific plugin. Use this to see what "
                "parameters are available and their current values before setting them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plugin_ref": {
                        "type": "string",
                        "description": (
                            "Plugin reference in format 'channel:slot' (e.g., '0:0' for "
                            "channel 0, slot 0) or just 'N' for channel N's first plugin"
                        )
                    }
                },
                "required": ["plugin_ref"]
            }
        },
        
        "set_param": {
            "description": (
                "Set a plugin parameter to a specific value. Values must be normalized "
                "to 0.0-1.0 range. Use get_params first to see available parameters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plugin_ref": {
                        "type": "string",
                        "description": (
                            "Plugin reference in format 'channel:slot' (e.g., '0:0')"
                        )
                    },
                    "index": {
                        "type": "integer",
                        "description": "Parameter index (0-based)",
                        "minimum": 0
                    },
                    "value01": {
                        "type": "number",
                        "description": "Parameter value normalized to 0.0-1.0 range",
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["plugin_ref", "index", "value01"]
            }
        },
        
        "set_note_batch": {
            "description": (
                "Add or modify a batch of MIDI notes in a channel. Each note has "
                "pitch (0-127), start time (in beats), duration (in beats), and "
                "velocity (1-127)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_ref": {
                        "type": "string",
                        "description": "Channel reference (e.g., '0' for channel 0)"
                    },
                    "notes": {
                        "type": "array",
                        "description": "Array of note objects to add/modify",
                        "items": {
                            "type": "object",
                            "properties": {
                                "pitch": {
                                    "type": "integer",
                                    "description": "MIDI note number (0-127, 60=middle C)",
                                    "minimum": 0,
                                    "maximum": 127
                                },
                                "start": {
                                    "type": "number",
                                    "description": "Start time in beats (quarter notes)",
                                    "minimum": 0.0
                                },
                                "duration": {
                                    "type": "number",
                                    "description": "Duration in beats",
                                    "minimum": 0.0
                                },
                                "velocity": {
                                    "type": "integer",
                                    "description": "Note velocity (1-127)",
                                    "minimum": 1,
                                    "maximum": 127
                                }
                            },
                            "required": ["pitch", "start", "duration", "velocity"]
                        }
                    }
                },
                "required": ["channel_ref", "notes"]
            }
        },
        
        "transport": {
            "description": (
                "Control FL Studio transport (playback controls). Available commands: "
                "play, stop, record, pause, rewind, fast_forward, loop_toggle, "
                "metronome_toggle"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Transport command to execute",
                        "enum": [
                            "play", "stop", "record", "pause", "rewind",
                            "fast_forward", "loop_toggle", "metronome_toggle"
                        ]
                    }
                },
                "required": ["cmd"]
            }
        },
        
        "mixer": {
            "description": (
                "Control mixer settings for a specific track. Can set volume or pan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Mixer action to perform",
                        "enum": ["set_volume", "set_pan"]
                    },
                    "track": {
                        "type": "integer",
                        "description": "Mixer track index (0-based)",
                        "minimum": 0
                    },
                    "value": {
                        "type": "number",
                        "description": (
                            "Value for the action. For volume: 0.0-1.0 (0.8=0dB). "
                            "For pan: -1.0 (left) to 1.0 (right), 0.0 (center)"
                        )
                    }
                },
                "required": ["action", "track", "value"]
            }
        },
        
        "channel": {
            "description": (
                "Select a channel in FL Studio by its index."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "select_index": {
                        "type": "integer",
                        "description": "Channel index to select (0-based)",
                        "minimum": 0
                    }
                },
                "required": ["select_index"]
            }
        }
    }


def get_tool_callable(tool_name: str) -> Optional[Callable]:
    """
    Get a callable stub for a tool.
    
    This returns placeholder functions that will be wired to actual IPC
    calls in a future PR. For now, they serve as documentation and type hints.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Callable function or None if tool doesn't exist
    """
    
    def list_state() -> Dict[str, Any]:
        """Get FL Studio state."""
        raise NotImplementedError("Tool execution not yet wired to IPC")
    
    def get_params(plugin_ref: str) -> Dict[str, Any]:
        """Get plugin parameters."""
        raise NotImplementedError("Tool execution not yet wired to IPC")
    
    def set_param(plugin_ref: str, index: int, value01: float) -> Dict[str, Any]:
        """Set plugin parameter."""
        raise NotImplementedError("Tool execution not yet wired to IPC")
    
    def set_note_batch(channel_ref: str, notes: list) -> Dict[str, Any]:
        """Set notes in channel."""
        raise NotImplementedError("Tool execution not yet wired to IPC")
    
    def transport(cmd: str) -> Dict[str, Any]:
        """Control transport."""
        raise NotImplementedError("Tool execution not yet wired to IPC")
    
    def mixer(action: str, track: int, value: float) -> Dict[str, Any]:
        """Control mixer."""
        raise NotImplementedError("Tool execution not yet wired to IPC")
    
    def channel(select_index: int) -> Dict[str, Any]:
        """Select channel."""
        raise NotImplementedError("Tool execution not yet wired to IPC")
    
    # Map tool names to callables
    tools = {
        "list_state": list_state,
        "get_params": get_params,
        "set_param": set_param,
        "set_note_batch": set_note_batch,
        "transport": transport,
        "mixer": mixer,
        "channel": channel,
    }
    
    return tools.get(tool_name)
