"""
ZeroMQ REQ client for FL Studio IPC communication.
Handles connection, reconnection, and message exchange with the controller app.
"""

import json
import time
import uuid
from typing import Dict, Any, Optional

try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    print("Warning: ZeroMQ not available. IPC client will run in mock mode.")


class IPCClient:
    """
    ZeroMQ REQ client with automatic reconnection and exponential backoff.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5555, 
                 timeout_ms: int = 1000, max_retries: int = 3):
        """
        Initialize the IPC client.
        
        Args:
            host: Server host address
            port: Server port
            timeout_ms: Socket timeout in milliseconds
            max_retries: Maximum number of retries before giving up
        """
        self.host = host
        self.port = port
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.connection_str = f"tcp://{host}:{port}"
        
        self.context = None
        self.socket = None
        self.connected = False
        self.last_error = None
        
        # Backoff parameters
        self.initial_backoff = 1.0  # seconds
        self.max_backoff = 30.0  # seconds
        self.backoff_multiplier = 2.0
        self.current_backoff = self.initial_backoff
        
        if ZMQ_AVAILABLE:
            self.context = zmq.Context()
    
    def connect(self) -> bool:
        """
        Connect to the server.
        
        Returns:
            True if connected successfully
        """
        if not ZMQ_AVAILABLE:
            print("ZMQ not available, running in mock mode")
            self.connected = False
            return False
        
        try:
            if self.socket:
                self.socket.close()
            
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
            self.socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
            self.socket.setsockopt(zmq.LINGER, 0)
            
            self.socket.connect(self.connection_str)
            self.connected = True
            self.current_backoff = self.initial_backoff
            self.last_error = None
            
            print(f"IPC client connected to {self.connection_str}")
            return True
            
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            print(f"Failed to connect to {self.connection_str}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"Error closing socket: {e}")
            finally:
                self.socket = None
        self.connected = False
    
    def send_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send a message and wait for response.
        
        Args:
            msg: Message dictionary to send
            
        Returns:
            Response dictionary, or None on failure
        """
        if not ZMQ_AVAILABLE:
            return self._mock_response(msg)
        
        retries = 0
        while retries < self.max_retries:
            if not self.connected:
                if not self.connect():
                    self._wait_backoff()
                    retries += 1
                    continue
            
            try:
                # Send message
                msg_json = json.dumps(msg)
                self.socket.send_string(msg_json)
                
                # Wait for response
                response_json = self.socket.recv_string()
                response = json.loads(response_json)
                
                # Reset backoff on success
                self.current_backoff = self.initial_backoff
                return response
                
            except zmq.Again:
                # Timeout
                self.last_error = "Request timeout"
                print(f"Request timeout on attempt {retries + 1}")
                self._reconnect()
                self._wait_backoff()
                retries += 1
                
            except zmq.ZMQError as e:
                self.last_error = str(e)
                print(f"ZMQ error: {e}")
                self._reconnect()
                self._wait_backoff()
                retries += 1
                
            except json.JSONDecodeError as e:
                self.last_error = f"JSON decode error: {e}"
                print(f"Invalid JSON response: {e}")
                return None
                
            except Exception as e:
                self.last_error = str(e)
                print(f"Unexpected error: {e}")
                self._reconnect()
                self._wait_backoff()
                retries += 1
        
        print(f"Failed to send message after {self.max_retries} attempts")
        return None
    
    def _reconnect(self):
        """Internal method to reconnect the socket."""
        self.disconnect()
        # Don't immediately reconnect; let the backoff handle it
    
    def _wait_backoff(self):
        """Wait with exponential backoff."""
        time.sleep(self.current_backoff)
        self.current_backoff = min(
            self.current_backoff * self.backoff_multiplier, 
            self.max_backoff
        )
    
    def _mock_response(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a mock response for testing without ZeroMQ.
        
        Args:
            msg: Request message
            
        Returns:
            Mock response
        """
        msg_type = msg.get("type", "unknown")
        msg_id = msg.get("id", str(uuid.uuid4()))
        
        # Mock different response types
        if msg_type == "ping":
            return {
                "type": "response",
                "id": msg_id,
                "payload": {"status": "ok", "message": "pong (mock)"}
            }
        elif msg_type == "get_state":
            return {
                "type": "response",
                "id": msg_id,
                "payload": {
                    "channels": [],
                    "plugins": [],
                    "mixer_tracks": [],
                    "fl_version": "mock"
                }
            }
        else:
            return {
                "type": "response",
                "id": msg_id,
                "payload": {"status": "ok", "message": f"Mock response for {msg_type}"}
            }
    
    def ping(self) -> bool:
        """
        Send a ping message to test connectivity.
        
        Returns:
            True if server responded
        """
        msg = {
            "type": "ping",
            "id": str(uuid.uuid4())
        }
        response = self.send_message(msg)
        return response is not None and response.get("type") != "error"
    
    def get_state(self) -> Optional[Dict[str, Any]]:
        """
        Get current FL Studio state.
        
        Returns:
            State dictionary or None
        """
        msg = {
            "type": "get_state",
            "id": str(uuid.uuid4())
        }
        response = self.send_message(msg)
        if response and response.get("type") == "response":
            return response.get("payload")
        return None
    
    def set_param(self, plugin_index: int, param_index: int, value: float) -> bool:
        """
        Set a plugin parameter value.
        
        Args:
            plugin_index: Plugin index
            param_index: Parameter index
            value: Normalized value (0-1)
            
        Returns:
            True if successful
        """
        msg = {
            "type": "set_param",
            "id": str(uuid.uuid4()),
            "payload": {
                "plugin_index": plugin_index,
                "param_index": param_index,
                "value": max(0.0, min(1.0, value))  # Clamp to 0-1
            }
        }
        response = self.send_message(msg)
        return response is not None and response.get("type") != "error"
    
    def send_transport_command(self, command: str) -> bool:
        """
        Send a transport command.
        
        Args:
            command: Transport command (play, stop, record, etc.)
            
        Returns:
            True if successful
        """
        msg = {
            "type": "transport",
            "id": str(uuid.uuid4()),
            "payload": {"command": command}
        }
        response = self.send_message(msg)
        return response is not None and response.get("type") != "error"
    
    def set_mixer_volume(self, track_index: int, volume: float) -> bool:
        """
        Set mixer track volume.
        
        Args:
            track_index: Mixer track index
            volume: Volume value (0-1)
            
        Returns:
            True if successful
        """
        msg = {
            "type": "mixer",
            "id": str(uuid.uuid4()),
            "payload": {
                "track_index": track_index,
                "action": "set_volume",
                "volume": max(0.0, min(1.0, volume))
            }
        }
        response = self.send_message(msg)
        return response is not None and response.get("type") != "error"
    
    def set_mixer_pan(self, track_index: int, pan: float) -> bool:
        """
        Set mixer track pan.
        
        Args:
            track_index: Mixer track index
            pan: Pan value (-1 to 1)
            
        Returns:
            True if successful
        """
        msg = {
            "type": "mixer",
            "id": str(uuid.uuid4()),
            "payload": {
                "track_index": track_index,
                "action": "set_pan",
                "pan": max(-1.0, min(1.0, pan))
            }
        }
        response = self.send_message(msg)
        return response is not None and response.get("type") != "error"
    
    def select_channel(self, channel_index: int) -> bool:
        """
        Select a channel.
        
        Args:
            channel_index: Channel index
            
        Returns:
            True if successful
        """
        msg = {
            "type": "channel",
            "id": str(uuid.uuid4()),
            "payload": {
                "action": "select_by_index",
                "index": channel_index
            }
        }
        response = self.send_message(msg)
        return response is not None and response.get("type") != "error"
    
    def __del__(self):
        """Cleanup on deletion."""
        self.disconnect()
        if self.context and ZMQ_AVAILABLE:
            try:
                self.context.term()
            except:
                pass
