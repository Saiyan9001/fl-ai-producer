#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window for FL-AI-Producer Desktop Application
"""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QTextEdit,
    QListWidget, QListWidgetItem, QCheckBox, QGroupBox, QProgressBar,
    QSplitter,
)
from PySide6.QtCore import Qt, QThread, Signal
import threading


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
        self._create_ai_assistant_tab()
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
    
    def _create_ai_assistant_tab(self):
        """Create AI Assistant tab with agent controls."""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Provider configuration section
        config_group = QGroupBox("Provider Configuration")
        config_layout = QVBoxLayout()
        
        # Provider selection
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Auto", "OpenAI", "Ollama"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addStretch()
        config_layout.addLayout(provider_layout)
        
        # Model name
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-4o-mini or llama3.1")
        model_layout.addWidget(self.model_input)
        config_layout.addLayout(model_layout)
        
        # API key (masked)
        apikey_layout = QHBoxLayout()
        apikey_layout.addWidget(QLabel("API Key:"))
        self.apikey_input = QLineEdit()
        self.apikey_input.setEchoMode(QLineEdit.Password)
        self.apikey_input.setPlaceholderText("Enter API key (for OpenAI)")
        apikey_layout.addWidget(self.apikey_input)
        config_layout.addLayout(apikey_layout)
        
        # Ollama host
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Ollama Host:"))
        self.ollama_host_input = QLineEdit()
        self.ollama_host_input.setPlaceholderText("http://127.0.0.1:11434")
        self.ollama_host_input.setText("http://127.0.0.1:11434")
        host_layout.addWidget(self.ollama_host_input)
        config_layout.addLayout(host_layout)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # Chat section with splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Chat input area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.addWidget(QLabel("Chat / Query:"))
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText(
            "Enter your request here, e.g.:\n"
            "- Set the cutoff on the first synth to 0.7\n"
            "- Add a C major chord to channel 0\n"
            "- Start playback"
        )
        self.chat_input.setMaximumHeight(120)
        chat_layout.addWidget(self.chat_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.preview_button = QPushButton("Preview Plan")
        self.preview_button.clicked.connect(self._on_preview_plan)
        button_layout.addWidget(self.preview_button)
        
        self.apply_button = QPushButton("Apply Plan")
        self.apply_button.clicked.connect(self._on_apply_plan)
        self.apply_button.setEnabled(False)
        button_layout.addWidget(self.apply_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        chat_layout.addLayout(button_layout)
        
        chat_widget.setLayout(chat_layout)
        splitter.addWidget(chat_widget)
        
        # Plan preview area
        preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(QLabel("Action Plan:"))
        self.plan_list = QListWidget()
        self.plan_list.setAlternatingRowColors(True)
        preview_layout.addWidget(self.plan_list)
        preview_widget.setLayout(preview_layout)
        splitter.addWidget(preview_widget)
        
        # Results/logs area
        results_widget = QWidget()
        results_layout = QVBoxLayout()
        results_layout.addWidget(QLabel("Results / Logs:"))
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        results_widget.setLayout(results_layout)
        splitter.addWidget(results_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([150, 250, 200])
        main_layout.addWidget(splitter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        widget.setLayout(main_layout)
        self.tabs.addTab(widget, "AI Assistant")
        
        # Initialize state
        self.current_plan = None
        self.cancel_flag = threading.Event()
        self._on_provider_changed(self.provider_combo.currentText())
    
    def _on_provider_changed(self, provider: str):
        """Handle provider selection change."""
        # Enable/disable fields based on provider
        is_openai = provider == "OpenAI" or provider == "Auto"
        is_ollama = provider == "Ollama" or provider == "Auto"
        
        self.apikey_input.setEnabled(is_openai)
        self.ollama_host_input.setEnabled(is_ollama)
        
        # Set default model
        if provider == "OpenAI":
            self.model_input.setPlaceholderText("gpt-4o-mini")
        elif provider == "Ollama":
            self.model_input.setPlaceholderText("llama3.1")
        else:
            self.model_input.setPlaceholderText("Auto-detect model")
    
    def _on_preview_plan(self):
        """Handle preview plan button click."""
        query = self.chat_input.toPlainText().strip()
        if not query:
            self.results_text.append("❌ Error: Please enter a query")
            return
        
        self.results_text.append(f"\n📋 Previewing plan for: {query}")
        self.results_text.append("⚠️ Note: Preview mode is not yet fully implemented in the UI")
        self.results_text.append("    This will call the agent with dry_run=True")
        self.results_text.append("    and display the proposed actions in the Action Plan list.")
        
        # TODO: Implement actual preview with agent
        # This would:
        # 1. Create provider based on configuration
        # 2. Call run_agent with dry_run=True
        # 3. Display actions in plan_list with checkboxes
        # 4. Enable apply_button
        
        self.apply_button.setEnabled(False)  # Would be True after preview
    
    def _on_apply_plan(self):
        """Handle apply plan button click."""
        if self.current_plan is None:
            self.results_text.append("❌ Error: No plan to apply. Preview a plan first.")
            return
        
        self.results_text.append("\n🚀 Applying plan...")
        self.results_text.append("⚠️ Note: Plan application is not yet fully implemented in the UI")
        self.results_text.append("    This would execute checked actions via IPC client")
        self.results_text.append("    and display results in the Results/Logs area.")
        
        # TODO: Implement actual execution
        # This would:
        # 1. Create IPC client
        # 2. Call run_agent with dry_run=False and filtered actions
        # 3. Display results for each action
        # 4. Show errors if any
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.cancel_flag.set()
        self.results_text.append("\n⚠️ Cancellation requested...")
    
    def _create_settings_tab(self):
        """Create settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        label = QLabel("Settings")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        widget.setLayout(layout)
        self.tabs.addTab(widget, "Settings")
