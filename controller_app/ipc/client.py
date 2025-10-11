"""
IPC Client for AI Agent

Simple REQ client used by the AI agent to send validated JSON commands
to FL Studio via ZeroMQ IPC at localhost:5555.
"""
import json
import uuid
from typing import Dict, Any, Optional, List
import zmq
from .schema import (
    MessageType,
    GetStateRequest,
    GetParamsRequest,
    SetParamRequest,
    SetNoteBatchRequest,
    TransportRequest,
    MixerRequest,
    ChannelRequest,
)


class IPCClient:
    """
    Simple IPC client for sending commands to FL Studio.
    
    Used by the AI agent to execute tool calls by sending validated
    JSON messages over ZeroMQ REQ/REP.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5555, timeout_ms: int = 5000):
        """
        Initialize IPC client.
        
        Args:
            host: Server host address
            port: Server port
            timeout_ms: Request timeout in milliseconds
        """
        self.host = host
        self.port = port
        self.timeout_ms = timeout_ms
        self.connection_str = f"tcp://{host}:{port}"
        
        self.context = zmq.Context()
        self.socket = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        Connect to the IPC server.
        
        Returns:
            True if connection successful
        """
        try:
            if self.socket:
                self.socket.close()
            
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
            self.socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.connect(self.connection_str)
            
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"Failed to connect to {self.connection_str}: {e}")
    
    def disconnect(self):
        """Disconnect from the IPC server."""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            finally:
                self.socket = None
        self._connected = False
    
    def call(self, msg_type: MessageType, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message and get response.
        
        Args:
            msg_type: Message type to send
            payload: Optional payload data
            
        Returns:
            Response payload dict
            
        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self._connected:
            raise RuntimeError("Not connected to IPC server. Call connect() first.")
        
        # Create message
        message = {
            "type": msg_type.value,
            "id": str(uuid.uuid4()),
        }
        if payload is not None:
            message["payload"] = payload
        
        try:
            # Send request
            self.socket.send_json(message)
            
            # Wait for response
            response = self.socket.recv_json()
            
            # Check for errors
            if response.get("type") == MessageType.ERROR.value:
                error_msg = response.get("payload", {}).get("error", "Unknown error")
                raise RuntimeError(f"IPC error: {error_msg}")
            
            return response.get("payload", {})
            
        except zmq.error.Again:
            raise TimeoutError(f"IPC request timed out after {self.timeout_ms}ms")
        except Exception as e:
            raise RuntimeError(f"IPC request failed: {e}")
    
    # Helper methods for specific operations
    
    def list_state(self) -> Dict[str, Any]:
        """
        Get current FL Studio state.
        
        Returns:
            Dict with channels, plugins, mixer_tracks, etc.
        """
        return self.call(MessageType.GET_STATE)
    
    def get_params(self, plugin_ref: str) -> Dict[str, Any]:
        """
        Get parameters for a plugin.
        
        Args:
            plugin_ref: Plugin reference (e.g., "0:0" or "0")
            
        Returns:
            Dict with plugin parameters
        """
        # Parse plugin reference
        if ":" in plugin_ref:
            channel_str, slot_str = plugin_ref.split(":", 1)
            channel_idx = int(channel_str)
            slot_idx = int(slot_str)
        else:
            channel_idx = int(plugin_ref)
            slot_idx = 0
        
        payload = {
            "plugin_index": channel_idx * 10 + slot_idx,  # Simple encoding
        }
        return self.call(MessageType.GET_PARAMS, payload)
    
    def set_param(self, plugin_ref: str, index: int, value01: float) -> Dict[str, Any]:
        """
        Set a plugin parameter.
        
        Args:
            plugin_ref: Plugin reference (e.g., "0:0")
            index: Parameter index
            value01: Normalized value (0.0-1.0), will be clamped
            
        Returns:
            Dict with success status
        """
        # Parse plugin reference
        if ":" in plugin_ref:
            channel_str, slot_str = plugin_ref.split(":", 1)
            channel_idx = int(channel_str)
            slot_idx = int(slot_str)
        else:
            channel_idx = int(plugin_ref)
            slot_idx = 0
        
        # Clamp value to 0-1 range
        value01 = max(0.0, min(1.0, value01))
        
        payload = {
            "plugin_index": channel_idx * 10 + slot_idx,
            "param_index": index,
            "value": value01,
        }
        return self.call(MessageType.SET_PARAM, payload)
    
    def set_note_batch(self, channel_ref: str, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Set MIDI notes in a channel.
        
        Args:
            channel_ref: Channel reference (e.g., "0")
            notes: List of note dicts with pitch, start, duration, velocity
            
        Returns:
            Dict with success status
        """
        channel_idx = int(channel_ref)
        
        # Validate notes
        validated_notes = []
        for note in notes:
            validated_note = {
                "pitch": max(0, min(127, note.get("pitch", 60))),
                "start": max(0.0, note.get("start", 0.0)),
                "duration": max(0.0, note.get("duration", 1.0)),
                "velocity": max(1, min(127, note.get("velocity", 100))),
            }
            validated_notes.append(validated_note)
        
        payload = {
            "channel_index": channel_idx,
            "notes": validated_notes,
        }
        return self.call(MessageType.SET_NOTE_BATCH, payload)
    
    def transport(self, cmd: str) -> Dict[str, Any]:
        """
        Control transport.
        
        Args:
            cmd: Transport command (play, stop, record, etc.)
            
        Returns:
            Dict with success status
        """
        valid_commands = [
            "play", "stop", "record", "pause", "rewind",
            "fast_forward", "loop_toggle", "metronome_toggle"
        ]
        
        if cmd not in valid_commands:
            raise ValueError(f"Invalid transport command: {cmd}. Must be one of {valid_commands}")
        
        payload = {"command": cmd}
        return self.call(MessageType.TRANSPORT, payload)
    
    def mixer(self, action: str, track: int, value: float) -> Dict[str, Any]:
        """
        Control mixer.
        
        Args:
            action: Mixer action (set_volume, set_pan)
            track: Mixer track index
            value: Value (0.0-1.0 for volume, -1.0-1.0 for pan)
            
        Returns:
            Dict with success status
        """
        valid_actions = ["set_volume", "set_pan"]
        
        if action not in valid_actions:
            raise ValueError(f"Invalid mixer action: {action}. Must be one of {valid_actions}")
        
        payload = {
            "action": action,
            "track": track,
            "value": value,
        }
        return self.call(MessageType.MIXER, payload)
    
    def channel(self, select_index: int) -> Dict[str, Any]:
        """
        Select a channel.
        
        Args:
            select_index: Channel index to select
            
        Returns:
            Dict with success status
        """
        payload = {
            "action": "select_by_index",
            "index": select_index,
        }
        return self.call(MessageType.CHANNEL, payload)
