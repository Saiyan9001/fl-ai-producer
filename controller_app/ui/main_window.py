#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window for FL-AI-Producer Desktop Application
"""
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    """Main application window with tabs for different features."""
    
    def __init__(self, ipc_server=None):
        """
        Initialize the main window.
        
        Args:
            ipc_server: IPC server instance for communication with FL Studio
        """
        super().__init__()
        self.ipc_server = ipc_server
        self.setWindowTitle("FL-AI-Producer")
        self.setMinimumSize(800, 600)
        
        # Create central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create tabs
        self._create_plugin_control_tab()
        self._create_ai_tab()
        self._create_settings_tab()
    
    def _create_plugin_control_tab(self):
        """Create plugin control tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Plugin Control")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        widget.setLayout(layout)
        self.tabs.addTab(widget, "Plugins")
    
    def _create_ai_tab(self):
        """Create AI transcription tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("AI Transcription")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        widget.setLayout(layout)
        self.tabs.addTab(widget, "AI")
    
    def _create_settings_tab(self):
        """Create settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Settings")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        widget.setLayout(layout)
        self.tabs.addTab(widget, "Settings")
