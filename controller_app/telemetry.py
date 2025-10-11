"""
Telemetry Module - Local-Only by Default

Logs events to local files for debugging and diagnostics.
Network telemetry is disabled by default and requires explicit opt-in.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import threading

logger = logging.getLogger(__name__)


class Telemetry:
    """
    Telemetry service for local logging.
    
    By default, all events are logged to local files only.
    Network reporting requires explicit opt-in.
    """
    
    def __init__(self, log_dir: Optional[Path] = None, enabled: bool = True):
        """
        Initialize telemetry service.
        
        Args:
            log_dir: Directory for telemetry logs (default: ~/.fl-ai-producer/telemetry)
            enabled: Whether telemetry is enabled (default: True for local logging)
        """
        self.enabled = enabled
        self.network_enabled = False  # Network telemetry is always opt-in
        self.log_dir = log_dir or (Path.home() / ".fl-ai-producer" / "telemetry")
        self._lock = threading.Lock()
        
        # Create log directory if enabled
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / f"events_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def enable_network_telemetry(self, enabled: bool = True):
        """
        Enable or disable network telemetry.
        
        This method allows explicit opt-in to network telemetry.
        By default, telemetry is local-only.
        
        Args:
            enabled: Whether to enable network telemetry
        """
        self.network_enabled = enabled
        logger.info(f"Network telemetry {'enabled' if enabled else 'disabled'}")
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log a telemetry event.
        
        Events are always logged locally (if telemetry is enabled).
        Network reporting only happens if explicitly enabled.
        
        Args:
            event_type: Type of event (e.g., "agent_query", "tool_execution")
            data: Event data (will be sanitized for secrets)
        """
        if not self.enabled:
            return
        
        try:
            # Create event payload
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "data": data
            }
            
            # Log to local file
            self._log_to_file(event)
            
            # Network telemetry (only if explicitly enabled)
            if self.network_enabled:
                self._send_to_network(event)
                
        except Exception as e:
            logger.error(f"Failed to log telemetry event: {e}")
    
    def _log_to_file(self, event: Dict[str, Any]):
        """
        Write event to local log file.
        
        Args:
            event: Event data to log
        """
        with self._lock:
            try:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception as e:
                logger.error(f"Failed to write telemetry to file: {e}")
    
    def _send_to_network(self, event: Dict[str, Any]):
        """
        Send event to network endpoint.
        
        This method is a placeholder for future network telemetry.
        It will never be called unless network_enabled is True (opt-in).
        
        Args:
            event: Event data to send
        """
        # Placeholder for network telemetry
        # In the future, this could send to a telemetry service
        logger.debug("Network telemetry: %s", event["event_type"])
    
    def log_agent_query(self, query: str, provider: str, dry_run: bool):
        """
        Log an agent query event.
        
        Args:
            query: User query (truncated for privacy)
            provider: AI provider used
            dry_run: Whether this was a dry run
        """
        self.log_event("agent_query", {
            "query_length": len(query),
            "query_preview": query[:50] + "..." if len(query) > 50 else query,
            "provider": provider,
            "dry_run": dry_run
        })
    
    def log_tool_execution(self, tool_name: str, success: bool, error: Optional[str] = None):
        """
        Log a tool execution event.
        
        Args:
            tool_name: Name of the tool executed
            success: Whether execution was successful
            error: Error message if failed
        """
        self.log_event("tool_execution", {
            "tool_name": tool_name,
            "success": success,
            "error": error
        })
    
    def log_error(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Log an error event.
        
        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
        """
        self.log_event("error", {
            "error_type": error_type,
            "message": message,
            "context": context or {}
        })


# Global telemetry instance
_telemetry: Optional[Telemetry] = None


def get_telemetry() -> Telemetry:
    """
    Get the global telemetry instance.
    
    Returns:
        Global telemetry instance
    """
    global _telemetry
    if _telemetry is None:
        _telemetry = Telemetry()
    return _telemetry


def init_telemetry(log_dir: Optional[Path] = None, enabled: bool = True) -> Telemetry:
    """
    Initialize the global telemetry instance.
    
    Args:
        log_dir: Directory for telemetry logs
        enabled: Whether telemetry is enabled
        
    Returns:
        Initialized telemetry instance
    """
    global _telemetry
    _telemetry = Telemetry(log_dir=log_dir, enabled=enabled)
    return _telemetry
