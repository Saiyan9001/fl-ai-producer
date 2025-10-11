"""
ZeroMQ server implementation for IPC
"""
import zmq
import json
import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, Callable, List
import traceback

from .schema import (
    Message, PingRequest, GetStateRequest, ListPluginsRequest,
    GetParamsRequest, SetParamRequest, SetNoteBatchRequest,
    TransportRequest, MixerRequest, ChannelRequest,
    MessageType, ErrorResponse, ResponseMessage
)

logger = logging.getLogger(__name__)

class IPCServer:
    """
    ZeroMQ server for handling IPC requests from FL Studio
    """
    
    def __init__(self, 
                 host: str = "127.0.0.1", 
                 port: int = 5555, 
                 context: Optional[zmq.Context] = None):
        """
        Initialize the ZeroMQ server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            context: Optional ZMQ context
        """
        self.host = host
        self.port = port
        self.context = context or zmq.Context()
        self.socket = None
        self.running = False
        self.thread = None
        self.handlers = {}
        self.clients = set()
        self.last_state = {
            "connected_clients": 0,
            "last_message_time": None,
            "plugins": [],
            "channels": [],
            "mixer_tracks": []
        }
        
        # Register default message handlers
        self.register_default_handlers()
        
    def start(self):
        """Start the server in a background thread"""
        if self.running:
            logger.warning("Server is already running")
            return
            
        logger.info(f"Starting ZeroMQ server on {self.host}:{self.port}")
        self.socket = self.context.socket(zmq.REP)
        connection_str = f"tcp://{self.host}:{self.port}"
        self.socket.bind(connection_str)
        
        self.running = True
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()
        logger.info(f"Server started on {connection_str}")
        
    def stop(self):
        """Stop the server"""
        if not self.running:
            logger.warning("Server is not running")
            return
            
        logger.info("Stopping server")
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.socket:
            self.socket.close()
        logger.info("Server stopped")
        
    def register_handler(self, message_type: MessageType, handler: Callable):
        """
        Register a handler function for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.handlers[message_type] = handler
        logger