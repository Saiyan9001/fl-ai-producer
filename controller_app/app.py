#!/usr/bin/env python3
"""
FL AI Producer Controller Application
Main entry point for the desktop application
"""
import sys
import logging
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from ui.main_window import MainWindow
from ipc.server import IPCServer
from telemetry import init_telemetry
from ai.guardrails import init_guardrails

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / ".fl-ai-producer" / "app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("fl-ai-producer")

def ensure_app_dirs():
    """Ensure application directories exist"""
    app_dir = Path.home() / ".fl-ai-producer"
    app_dir.mkdir(exist_ok=True)
    cache_dir = app_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    return app_dir, cache_dir

def main():
    """Main application entry point"""
    # Ensure application directories exist
    app_dir, cache_dir = ensure_app_dirs()
    
    # Initialize telemetry (local-only by default)
    telemetry = init_telemetry(log_dir=app_dir / "telemetry", enabled=True)
    logger.info("Telemetry initialized (local-only)")
    
    # Initialize guardrails with default limits
    guardrails = init_guardrails()
    logger.info("Guardrails initialized")
    
    # Create Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("FL AI Producer")
    app.setOrganizationName("FL AI Producer")
    
    # Create and start the IPC Server
    ipc_server = IPCServer()
    ipc_server.start()
    
    # Create main window
    window = MainWindow(ipc_server)
    window.show()
    
    # Set up a timer to periodically process IPC events
    timer = QTimer()
    timer.timeout.connect(ipc_server.process_events)
    timer.start(50)  # Check every 50ms
    
    # Run the application
    exit_code = app.exec()
    
    # Shutdown
    ipc_server.stop()
    logger.info("Application exiting with code %d", exit_code)
    return exit_code

if __name__ == "__main__":
    sys.exit(main())