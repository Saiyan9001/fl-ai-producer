"""
Test IPC roundtrip communication between controller app and FL Studio script.
"""

import sys
import os
import pytest
import time
import threading
import json
from typing import Dict, Any

# Add paths for imports
test_dir = os.path.dirname(os.path.abspath(__file__))
controller_app_dir = os.path.dirname(test_dir)
repo_root = os.path.dirname(controller_app_dir)
fl_scripts_dir = os.path.join(repo_root, 'fl_scripts')

if controller_app_dir not in sys.path:
    sys.path.insert(0, controller_app_dir)
if fl_scripts_dir not in sys.path:
    sys.path.insert(0, fl_scripts_dir)

# Import modules
from controller.ipc_client import IPCClient
from shared.message_schemas import (
    MessageType, TransportCommand, create_message, create_response, create_error
)

# Try to import ZeroMQ for server
try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False


class MockIPCServer:
    """
    Mock IPC server for testing the client without the full controller app.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5556):
        """Initialize mock server with different port to avoid conflicts."""
        self.host = host
        self.port = port
        self.running = False
        self.thread = None
        self.context = None
        self.socket = None
        self.received_messages = []
        
    def start(self):
        """Start the mock server in a background thread."""
        if not ZMQ_AVAILABLE:
            pytest.skip("ZeroMQ not available for testing")
            
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        
        self.running = True
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()
        time.sleep(0.1)  # Give server time to start
        
    def stop(self):
        """Stop the mock server."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
            
    def _server_loop(self):
        """Main server loop."""
        while self.running:
            try:
                # Set timeout so we can check running flag
                self.socket.setsockopt(zmq.RCVTIMEO, 100)
                
                # Receive message
                msg_json = self.socket.recv_string()
                msg = json.loads(msg_json)
                self.received_messages.append(msg)
                
                # Generate response based on message type
                response = self._handle_message(msg)
                
                # Send response
                response_json = json.dumps(response)
                self.socket.send_string(response_json)
                
            except zmq.Again:
                # Timeout, continue
                continue
            except Exception as e:
                print(f"Mock server error: {e}")
                break
                
    def _handle_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a received message and generate response."""
        msg_type = msg.get("type")
        msg_id = msg.get("id", "test-id")
        
        if msg_type == MessageType.PING:
            return create_response(msg_id, {"status": "ok", "message": "pong"})
            
        elif msg_type == MessageType.GET_STATE:
            return create_response(msg_id, {
                "channels": [
                    {"index": 0, "name": "Test Channel", "plugin_index": None, "plugin_name": None}
                ],
                "plugins": [],
                "mixer_tracks": [
                    {"index": 0, "name": "Master", "volume": 0.8, "pan": 0.0, "mute": False, "solo": False}
                ],
                "fl_version": "Mock 1.0"
            })
            
        elif msg_type == MessageType.SET_PARAM:
            payload = msg.get("payload", {})
            if "param_index" not in payload or "value" not in payload:
                return create_error(msg_id, "Missing required fields")
            return create_response(msg_id, {"status": "ok"})
            
        elif msg_type == MessageType.TRANSPORT:
            payload = msg.get("payload", {})
            if "command" not in payload:
                return create_error(msg_id, "Missing command")
            return create_response(msg_id, {"status": "ok"})
            
        elif msg_type == MessageType.MIXER:
            return create_response(msg_id, {"status": "ok"})
            
        elif msg_type == MessageType.CHANNEL:
            return create_response(msg_id, {"status": "ok"})
            
        else:
            return create_error(msg_id, f"Unknown message type: {msg_type}")


@pytest.fixture
def mock_server():
    """Fixture providing a mock IPC server."""
    if not ZMQ_AVAILABLE:
        pytest.skip("ZeroMQ not available for testing")
        
    server = MockIPCServer(port=5556)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def ipc_client(mock_server):
    """Fixture providing an IPC client connected to mock server."""
    client = IPCClient(host="127.0.0.1", port=5556, timeout_ms=1000)
    client.connect()
    yield client
    client.disconnect()


def test_client_creation():
    """Test that IPC client can be created."""
    client = IPCClient()
    assert client is not None
    assert client.host == "127.0.0.1"
    assert client.port == 5555


def test_client_connect(mock_server):
    """Test client connection to server."""
    client = IPCClient(host="127.0.0.1", port=5556)
    result = client.connect()
    
    if ZMQ_AVAILABLE:
        assert result is True
        assert client.connected is True
    else:
        assert result is False
        
    client.disconnect()


def test_ping(ipc_client, mock_server):
    """Test ping message roundtrip."""
    result = ipc_client.ping()
    
    assert result is True
    assert len(mock_server.received_messages) > 0
    
    last_msg = mock_server.received_messages[-1]
    assert last_msg["type"] == MessageType.PING


def test_get_state(ipc_client, mock_server):
    """Test get_state message roundtrip."""
    state = ipc_client.get_state()
    
    assert state is not None
    assert "channels" in state
    assert "plugins" in state
    assert "mixer_tracks" in state
    assert "fl_version" in state
    
    # Check structure
    assert isinstance(state["channels"], list)
    assert isinstance(state["mixer_tracks"], list)
    
    # Check received message
    last_msg = mock_server.received_messages[-1]
    assert last_msg["type"] == MessageType.GET_STATE


def test_set_param(ipc_client, mock_server):
    """Test set_param message roundtrip."""
    result = ipc_client.set_param(
        plugin_index=0,
        param_index=5,
        value=0.75
    )
    
    assert result is True
    
    # Check received message
    last_msg = mock_server.received_messages[-1]
    assert last_msg["type"] == MessageType.SET_PARAM
    assert last_msg["payload"]["plugin_index"] == 0
    assert last_msg["payload"]["param_index"] == 5
    assert last_msg["payload"]["value"] == 0.75


def test_set_param_clamping(ipc_client, mock_server):
    """Test that parameter values are clamped to 0-1."""
    # Test value > 1
    result = ipc_client.set_param(plugin_index=0, param_index=0, value=1.5)
    assert result is True
    
    last_msg = mock_server.received_messages[-1]
    assert last_msg["payload"]["value"] == 1.0
    
    # Test value < 0
    result = ipc_client.set_param(plugin_index=0, param_index=0, value=-0.5)
    assert result is True
    
    last_msg = mock_server.received_messages[-1]
    assert last_msg["payload"]["value"] == 0.0


def test_transport_commands(ipc_client, mock_server):
    """Test transport command messages."""
    commands = [
        TransportCommand.PLAY,
        TransportCommand.STOP,
        TransportCommand.RECORD
    ]
    
    for command in commands:
        result = ipc_client.send_transport_command(command)
        assert result is True
        
        last_msg = mock_server.received_messages[-1]
        assert last_msg["type"] == MessageType.TRANSPORT
        assert last_msg["payload"]["command"] == command


def test_mixer_volume(ipc_client, mock_server):
    """Test mixer volume control."""
    result = ipc_client.set_mixer_volume(track_index=0, volume=0.5)
    
    assert result is True
    
    last_msg = mock_server.received_messages[-1]
    assert last_msg["type"] == MessageType.MIXER
    assert last_msg["payload"]["track_index"] == 0
    assert last_msg["payload"]["action"] == "set_volume"
    assert last_msg["payload"]["volume"] == 0.5


def test_mixer_pan(ipc_client, mock_server):
    """Test mixer pan control."""
    result = ipc_client.set_mixer_pan(track_index=1, pan=-0.5)
    
    assert result is True
    
    last_msg = mock_server.received_messages[-1]
    assert last_msg["type"] == MessageType.MIXER
    assert last_msg["payload"]["action"] == "set_pan"
    assert last_msg["payload"]["pan"] == -0.5


def test_channel_select(ipc_client, mock_server):
    """Test channel selection."""
    result = ipc_client.select_channel(channel_index=3)
    
    assert result is True
    
    last_msg = mock_server.received_messages[-1]
    assert last_msg["type"] == MessageType.CHANNEL
    assert last_msg["payload"]["action"] == "select_by_index"
    assert last_msg["payload"]["index"] == 3


def test_reconnection():
    """Test that client handles connection failures gracefully."""
    # Try to connect to non-existent server
    client = IPCClient(host="127.0.0.1", port=9999, timeout_ms=100, max_retries=1)
    
    # This should fail but not crash
    result = client.ping()
    
    # In mock mode, this returns a mock response
    # In real mode with ZMQ, this should return None after retries
    if not ZMQ_AVAILABLE:
        assert result is not None  # Mock mode returns something
    
    client.disconnect()


def test_mock_mode_without_zmq():
    """Test that client works in mock mode when ZMQ is not available."""
    client = IPCClient()
    
    # Even without ZMQ, client should be created
    assert client is not None
    
    # Mock responses should be returned
    if not ZMQ_AVAILABLE:
        result = client.ping()
        assert result is not None  # Should get mock response


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
