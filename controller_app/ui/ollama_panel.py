#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama Panel - Local Model Management UI

Provides a UI panel for managing Ollama local models:
- Display host, version, and model list with sizes
- Pull new models with progress tracking
- Set default model in configuration
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QProgressBar,
    QGroupBox, QHeaderView, QMessageBox
)
from PySide6.QtCore import QThread, Signal
from typing import Optional
import os


class PullModelThread(QThread):
    """Background thread for pulling Ollama models."""
    
    progress_update = Signal(str, float)  # (status, progress)
    finished = Signal(bool, str)  # (success, message)
    
    def __init__(self, host: str, model: str):
        super().__init__()
        self.host = host
        self.model = model
    
    def run(self):
        """Pull model in background thread."""
        try:
            from controller_app.ai.providers.ollama_provider import OllamaProvider
            provider = OllamaProvider(host=self.host)
            
            for progress_data in provider.pull_model(self.model):
                status = progress_data.get("status", "")
                
                # Calculate progress percentage if available
                total = progress_data.get("total", 0)
                completed = progress_data.get("completed", 0)
                
                if total > 0:
                    progress_pct = (completed / total) * 100
                else:
                    progress_pct = 0
                
                self.progress_update.emit(status, progress_pct)
                
                # Check for errors
                if "error" in progress_data:
                    self.finished.emit(False, progress_data["error"])
                    return
            
            self.finished.emit(True, f"Model '{self.model}' pulled successfully!")
            
        except Exception as e:
            self.finished.emit(False, str(e))


class RefreshModelsThread(QThread):
    """Background thread for refreshing model list."""
    
    finished = Signal(bool, object, str)  # (success, models_list, error_message)
    
    def __init__(self, host: str):
        super().__init__()
        self.host = host
    
    def run(self):
        """Refresh models in background thread."""
        try:
            from controller_app.ai.providers.ollama_provider import OllamaProvider
            provider = OllamaProvider(host=self.host)
            models = provider.list_models()
            self.finished.emit(True, models, "")
        except Exception as e:
            self.finished.emit(False, [], str(e))


class OllamaPanel(QWidget):
    """Panel for managing local Ollama models."""
    
    def __init__(self, ollama_host: str = "http://127.0.0.1:11434"):
        """
        Initialize Ollama panel.
        
        Args:
            ollama_host: Ollama server URL
        """
        super().__init__()
        self.ollama_host = ollama_host
        self.pull_thread: Optional[PullModelThread] = None
        self.refresh_thread: Optional[RefreshModelsThread] = None
        
        self._init_ui()
        self._refresh_models()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Connection info section
        conn_group = QGroupBox("Ollama Connection")
        conn_layout = QVBoxLayout()
        
        # Host and version display
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Host:"))
        self.host_label = QLabel(self.ollama_host)
        self.host_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.host_label)
        info_layout.addStretch()
        
        info_layout.addWidget(QLabel("Version:"))
        self.version_label = QLabel("Checking...")
        self.version_label.setStyleSheet("font-style: italic;")
        info_layout.addWidget(self.version_label)
        info_layout.addStretch()
        
        conn_layout.addLayout(info_layout)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Models list section
        models_group = QGroupBox("Local Models")
        models_layout = QVBoxLayout()
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_models)
        refresh_layout.addWidget(self.refresh_button)
        refresh_layout.addStretch()
        models_layout.addLayout(refresh_layout)
        
        # Models table
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(4)
        self.models_table.setHorizontalHeaderLabels(["Model Name", "Size", "Modified", "Action"])
        self.models_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.models_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.models_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.models_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.models_table.setAlternatingRowColors(True)
        self.models_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.models_table.setSelectionBehavior(QTableWidget.SelectRows)
        models_layout.addWidget(self.models_table)
        
        models_group.setLayout(models_layout)
        layout.addWidget(models_group)
        
        # Pull model section
        pull_group = QGroupBox("Pull New Model")
        pull_layout = QVBoxLayout()
        
        # Input field
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Model Name:"))
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g., llama3.1, mistral, codellama")
        input_layout.addWidget(self.model_input)
        
        self.pull_button = QPushButton("Pull Model")
        self.pull_button.clicked.connect(self._pull_model)
        input_layout.addWidget(self.pull_button)
        
        pull_layout.addLayout(input_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        pull_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        pull_layout.addWidget(self.status_label)
        
        pull_group.setLayout(pull_layout)
        layout.addWidget(pull_group)
        
        self.setLayout(layout)
    
    def _refresh_models(self):
        """Refresh the list of models."""
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")
        self.version_label.setText("Checking...")
        
        # Start background thread to refresh
        self.refresh_thread = RefreshModelsThread(self.ollama_host)
        self.refresh_thread.finished.connect(self._on_refresh_finished)
        self.refresh_thread.start()
    
    def _on_refresh_finished(self, success: bool, models: list, error_msg: str):
        """Handle refresh completion."""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh")
        
        if success:
            self._update_models_table(models)
            self._update_version()
        else:
            self.version_label.setText("Not available")
            self.models_table.setRowCount(0)
            
            # Show error in status label
            self.status_label.setText(
                f"⚠️ Could not connect to Ollama: {error_msg}\n"
                "Please ensure Ollama is installed and running."
            )
            self.status_label.setStyleSheet("color: orange;")
    
    def _update_models_table(self, models: list):
        """Update the models table with current models."""
        self.models_table.setRowCount(len(models))
        
        for row, model in enumerate(models):
            # Model name
            name = model.get("name", "unknown")
            name_item = QTableWidgetItem(name)
            self.models_table.setItem(row, 0, name_item)
            
            # Size
            size = model.get("size", 0)
            size_str = self._format_size(size)
            size_item = QTableWidgetItem(size_str)
            self.models_table.setItem(row, 1, size_item)
            
            # Modified date
            modified = model.get("modified_at", "")
            if modified:
                # Format the date nicely
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                    modified_str = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    modified_str = modified[:16]
            else:
                modified_str = "unknown"
            modified_item = QTableWidgetItem(modified_str)
            self.models_table.setItem(row, 2, modified_item)
            
            # Make Default button
            make_default_btn = QPushButton("Make Default")
            make_default_btn.clicked.connect(
                lambda checked=False, m=name: self._make_default(m)
            )
            self.models_table.setCellWidget(row, 3, make_default_btn)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_idx = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_idx < len(units) - 1:
            size /= 1024
            unit_idx += 1
        
        return f"{size:.1f} {units[unit_idx]}"
    
    def _update_version(self):
        """Update Ollama version display."""
        try:
            from controller_app.ai.providers.ollama_provider import OllamaProvider
            provider = OllamaProvider(host=self.ollama_host)
            version = provider.show_version()
            self.version_label.setText(version)
            self.version_label.setStyleSheet("font-weight: bold; color: green;")
        except Exception:
            self.version_label.setText("Not available")
            self.version_label.setStyleSheet("color: gray;")
    
    def _pull_model(self):
        """Start pulling a new model."""
        model_name = self.model_input.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Input Required", "Please enter a model name to pull.")
            return
        
        # Disable controls during pull
        self.pull_button.setEnabled(False)
        self.model_input.setEnabled(False)
        self.refresh_button.setEnabled(False)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Pulling model '{model_name}'...")
        self.status_label.setStyleSheet("color: blue;")
        
        # Start background thread
        self.pull_thread = PullModelThread(self.ollama_host, model_name)
        self.pull_thread.progress_update.connect(self._on_pull_progress)
        self.pull_thread.finished.connect(self._on_pull_finished)
        self.pull_thread.start()
    
    def _on_pull_progress(self, status: str, progress: float):
        """Handle pull progress updates."""
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(f"Pulling: {status} ({progress:.1f}%)")
    
    def _on_pull_finished(self, success: bool, message: str):
        """Handle pull completion."""
        self.pull_button.setEnabled(True)
        self.model_input.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText(f"✓ {message}")
            self.status_label.setStyleSheet("color: green;")
            self.model_input.clear()
            
            # Refresh model list
            self._refresh_models()
        else:
            self.status_label.setText(f"✗ Error: {message}")
            self.status_label.setStyleSheet("color: red;")
    
    def _make_default(self, model_name: str):
        """Set a model as the default in configuration."""
        # Update environment variable (runtime only)
        os.environ["OLLAMA_MODEL"] = model_name
        
        # Show confirmation
        QMessageBox.information(
            self,
            "Default Model Updated",
            f"Model '{model_name}' has been set as the default for this session.\n\n"
            "To make this permanent, add this line to your .env file:\n"
            f"OLLAMA_MODEL={model_name}"
        )
        
        self.status_label.setText(f"✓ Default model set to: {model_name}")
        self.status_label.setStyleSheet("color: green;")
    
    def update_host(self, new_host: str):
        """Update the Ollama host URL."""
        self.ollama_host = new_host
        self.host_label.setText(new_host)
        self._refresh_models()
    
    def closeEvent(self, event):
        """Handle widget close event - cleanup threads."""
        # Wait for threads to finish
        if self.pull_thread and self.pull_thread.isRunning():
            self.pull_thread.quit()
            self.pull_thread.wait(1000)  # Wait max 1 second
        
        if self.refresh_thread and self.refresh_thread.isRunning():
            self.refresh_thread.quit()
            self.refresh_thread.wait(1000)  # Wait max 1 second
        
        super().closeEvent(event)
