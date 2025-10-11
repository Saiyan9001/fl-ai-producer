"""
Schema definitions for IPC messages
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator

class MessageType(str, Enum):
    """Enumeration of message types"""
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

class TransportCommand(str, Enum):
    """Enumeration of transport commands"""
    PLAY = "play"
    STOP = "stop"
    RECORD = "record"
    PAUSE = "pause"
    REWIND = "rewind"
    FAST_FORWARD = "fast_forward"
    LOOP_TOGGLE = "loop_toggle"
    METRONOME_TOGGLE = "metronome_toggle"

class Note(BaseModel):
    """Schema for a MIDI note"""
    pitch: int = Field(..., ge=0, le=127)
    start: float = Field(..., ge=0)
    duration: float = Field(..., gt=0)
    velocity: int = Field(..., ge=1, le=127)

class PluginParam(BaseModel):
    """Schema for a plugin parameter"""
    index: int
    name: str
    value: float
    min_value: float = 0.0
    max_value: float = 1.0
    is_discrete: bool = False
    labels: Optional[List[str]] = None

class Plugin(BaseModel):
    """Schema for a plugin"""
    index: int
    name: str
    parameters: Optional[Dict[str, PluginParam]] = None

class Channel(BaseModel):
    """Schema for a channel"""
    index: int
    name: str
    plugin_index: Optional[int] = None
    plugin_name: Optional[str] = None

class MixerTrack(BaseModel):
    """Schema for a mixer track"""
    index: int
    name: str
    volume: float
    pan: float
    mute: bool
    solo: bool

# Base message model
class Message(BaseModel):
    """Base schema for all messages"""
    type: MessageType
    id: str
    payload: Optional[Dict[str, Any]] = None

# Request message models
class PingRequest(Message):
    """Ping request message"""
    type: MessageType = MessageType.PING

class GetStateRequest(Message):
    """Get state request message"""
    type: MessageType = MessageType.GET_STATE

class ListPluginsRequest(Message):
    """List plugins request message"""
    type: MessageType = MessageType.LIST_PLUGINS

class GetParamsRequest(Message):
    """Get parameters request message"""
    type: MessageType = MessageType.GET_PARAMS
    payload: Dict[str, Any] = Field(...)
    
    @validator('payload')
    def validate_plugin_ref(cls, payload):
        """Validate plugin reference in payload"""
        if 'plugin_index' not in payload and 'plugin_name' not in payload:
            raise ValueError("Must provide either plugin_index or plugin_name")
        return payload

class SetParamRequest(Message):
    """Set parameter request message"""
    type: MessageType = MessageType.SET_PARAM
    payload: Dict[str, Any] = Field(...)
    
    @validator('payload')
    def validate_param_data(cls, payload):
        """Validate parameter data in payload"""
        required_fields = ['param_index', 'value']
        plugin_ref = ['plugin_index', 'plugin_name']
        
        # Check required fields
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")
        
        # Check plugin reference
        if not any(ref in payload for ref in plugin_ref):
            raise ValueError("Must provide either plugin_index or plugin_name")
            
        # Validate value range
        if not 0 <= payload['value'] <= 1:
            raise ValueError("Value must be between 0 and 1")
            
        return payload

class SetNoteBatchRequest(Message):
    """Set note batch request message"""
    type: MessageType = MessageType.SET_NOTE_BATCH
    payload: Dict[str, Any] = Field(...)
    
    @validator('payload')
    def validate_notes_data(cls, payload):
        """Validate notes data in payload"""
        if 'notes' not in payload:
            raise ValueError("Missing required field: notes")
            
        if 'channel_index' not in payload:
            raise ValueError("Missing required field: channel_index")
            
        return payload

class TransportRequest(Message):
    """Transport request message"""
    type: MessageType = MessageType.TRANSPORT
    payload: Dict[str, Any] = Field(...)
    
    @validator('payload')
    def validate_command(cls, payload):
        """Validate transport command in payload"""
        if 'command' not in payload:
            raise ValueError("Missing required field: command")
            
        if payload['command'] not in [cmd.value for cmd in TransportCommand]:
            valid_commands = [cmd.value for cmd in TransportCommand]
            raise ValueError(f"Invalid transport command. Must be one of: {valid_commands}")
            
        return payload

class MixerRequest(Message):
    """Mixer request message"""
    type: MessageType = MessageType.MIXER
    payload: Dict[str, Any] = Field(...)
    
    @validator('payload')
    def validate_mixer_data(cls, payload):
        """Validate mixer data in payload"""
        if 'track_index' not in payload:
            raise ValueError("Missing required field: track_index")
            
        if 'action' not in payload:
            raise ValueError("Missing required field: action")
            
        valid_actions = ['set_volume', 'set_pan', 'toggle_mute', 'toggle_solo']
        if payload['action'] not in valid_actions:
            raise ValueError(f"Invalid mixer action. Must be one of: {valid_actions}")
            
        # Check for required action-specific fields
        if payload['action'] == 'set_volume' and 'volume' not in payload:
            raise ValueError("Missing required field for set_volume: volume")
            
        if payload['action'] == 'set_pan' and 'pan' not in payload:
            raise ValueError("Missing required field for set_pan: pan")
            
        return payload

class ChannelRequest(Message):
    """Channel request message"""
    type: MessageType = MessageType.CHANNEL
    payload: Dict[str, Any] = Field(...)
    
    @validator('payload')
    def validate_channel_data(cls, payload):
        """Validate channel data in payload"""
        if 'action' not in payload:
            raise ValueError("Missing required field: action")
            
        valid_actions = ['select_by_index', 'select_by_name']
        if payload['action'] not in valid_actions:
            raise ValueError(f"Invalid channel action. Must be one of: {valid_actions}")
            
        # Check for required action-specific fields
        if payload['action'] == 'select_by_index' and 'index' not in payload:
            raise ValueError("Missing required field for select_by_index: index")
            
        if payload['action'] == 'select_by_name' and 'name' not in payload:
            raise ValueError("Missing required field for select_by_name: name")
            
        return payload

# Response message models
class ErrorResponse(Message):
    """Error response message"""
    type: MessageType = MessageType.ERROR
    payload: Dict[str, Any] = Field(...)
    
    @validator('payload')
    def validate_error_data(cls, payload):
        """Validate error data in payload"""
        if 'error' not in payload:
            raise ValueError("Missing required field: error")
        return payload

class ResponseMessage(Message):
    """Generic response message"""
    type: MessageType = MessageType.RESPONSE