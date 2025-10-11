"""
Message schema definitions for FL Studio IPC communication.
This mirrors controller_app/ipc/schema.py but uses simple dicts for FL Studio compatibility.
"""

from enum import Enum
from typing import Dict, List, Optional, Any

# Message Types
class MessageType:
    """Message type constants"""
    PING = "ping"
    GET_STATE = "get_state"
    LIST_PLUGINS = "list_plugins"
    GET_PARAMS = "get_params"
    SET_PARAM = "set_param"
    SET_NOTE_BATCH = "set_note_batch"
    TRANSPORT = "transport"
    MIXER = "mixer"
    CHANNEL = "channel"
    ERROR = "error"
    RESPONSE = "response"


class TransportCommand:
    """Transport command constants"""
    PLAY = "play"
    STOP = "stop"
    RECORD = "record"
    PAUSE = "pause"
    REWIND = "rewind"
    FAST_FORWARD = "fast_forward"
    LOOP_TOGGLE = "loop_toggle"
    METRONOME_TOGGLE = "metronome_toggle"


def create_message(msg_type: str, msg_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a message dictionary.
    
    Args:
        msg_type: Message type
        msg_id: Unique message ID
        payload: Optional message payload
        
    Returns:
        Message dictionary
    """
    msg = {
        "type": msg_type,
        "id": msg_id,
    }
    if payload is not None:
        msg["payload"] = payload
    return msg


def create_response(msg_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a response message.
    
    Args:
        msg_id: Message ID to respond to
        payload: Response payload
        
    Returns:
        Response message dictionary
    """
    return create_message(MessageType.RESPONSE, msg_id, payload)


def create_error(msg_id: str, error: str) -> Dict[str, Any]:
    """
    Create an error message.
    
    Args:
        msg_id: Message ID to respond to
        error: Error message
        
    Returns:
        Error message dictionary
    """
    return create_message(MessageType.ERROR, msg_id, {"error": error})


def validate_message(msg: Dict[str, Any]) -> bool:
    """
    Validate a message has required fields.
    
    Args:
        msg: Message dictionary
        
    Returns:
        True if valid
    """
    if not isinstance(msg, dict):
        return False
    if "type" not in msg or "id" not in msg:
        return False
    return True


def create_state_snapshot(channels: List[Dict], plugins: List[Dict], 
                          mixer_tracks: List[Dict], fl_version: str = "") -> Dict[str, Any]:
    """
    Create a state snapshot payload.
    
    Args:
        channels: List of channel dictionaries
        plugins: List of plugin dictionaries
        mixer_tracks: List of mixer track dictionaries
        fl_version: FL Studio version string
        
    Returns:
        State snapshot dictionary
    """
    return {
        "channels": channels,
        "plugins": plugins,
        "mixer_tracks": mixer_tracks,
        "fl_version": fl_version
    }


def create_plugin_param(index: int, name: str, value: float, 
                       min_value: float = 0.0, max_value: float = 1.0) -> Dict[str, Any]:
    """
    Create a plugin parameter dictionary.
    
    Args:
        index: Parameter index
        name: Parameter name
        value: Current value (0-1 normalized)
        min_value: Minimum value
        max_value: Maximum value
        
    Returns:
        Parameter dictionary
    """
    return {
        "index": index,
        "name": name,
        "value": value,
        "min_value": min_value,
        "max_value": max_value
    }


def create_channel_info(index: int, name: str, plugin_index: Optional[int] = None, 
                       plugin_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a channel info dictionary.
    
    Args:
        index: Channel index
        name: Channel name
        plugin_index: Optional plugin index
        plugin_name: Optional plugin name
        
    Returns:
        Channel info dictionary
    """
    return {
        "index": index,
        "name": name,
        "plugin_index": plugin_index,
        "plugin_name": plugin_name
    }


def create_mixer_track_info(index: int, name: str, volume: float, 
                            pan: float, mute: bool, solo: bool) -> Dict[str, Any]:
    """
    Create a mixer track info dictionary.
    
    Args:
        index: Track index
        name: Track name
        volume: Volume (0-1)
        pan: Pan (-1 to 1)
        mute: Mute state
        solo: Solo state
        
    Returns:
        Mixer track info dictionary
    """
    return {
        "index": index,
        "name": name,
        "volume": volume,
        "pan": pan,
        "mute": mute,
        "solo": solo
    }
