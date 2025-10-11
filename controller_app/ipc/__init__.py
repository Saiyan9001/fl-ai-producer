"""
IPC module for FL AI Producer
Contains server and client implementations for ZeroMQ-based communication
"""
from .client import IPCClient

__all__ = [
    "IPCClient",
]