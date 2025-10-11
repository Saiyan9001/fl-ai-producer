#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtual MIDI (loopMIDI) fallback implementation
"""
import logging

logger = logging.getLogger(__name__)


class VirtualMIDI:
    """Virtual MIDI device handler for loopMIDI fallback."""
    
    def __init__(self, port_name: str = "FL-AI-Producer"):
        """
        Initialize virtual MIDI device.
        
        Args:
            port_name: Name of the virtual MIDI port
        """
        self.port_name = port_name
        self.connected = False
        logger.info(f"Virtual MIDI initialized for port: {port_name}")
    
    def connect(self) -> bool:
        """
        Connect to the virtual MIDI device.
        
        Returns:
            True if connected successfully
        """
        logger.info(f"Connecting to virtual MIDI port: {self.port_name}")
        self.connected = True
        return self.connected
    
    def disconnect(self):
        """Disconnect from the virtual MIDI device."""
        logger.info("Disconnecting from virtual MIDI")
        self.connected = False
    
    def send_message(self, message: bytes):
        """
        Send a MIDI message.
        
        Args:
            message: MIDI message bytes
        """
        if not self.connected:
            logger.warning("Cannot send message: not connected")
            return
        logger.debug(f"Sending MIDI message: {message.hex()}")
