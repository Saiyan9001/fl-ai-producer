#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reusable UI components for FL-AI-Producer
"""
from PySide6.QtWidgets import (
    QWidget, QPushButton, QSlider, QLabel, QVBoxLayout, QHBoxLayout,
    QComboBox, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QPalette
from typing import Optional


class ParameterSlider(QWidget):
    """A slider widget for controlling plugin parameters."""
    
    valueChanged = Signal(float)
    
    def __init__(self, name: str, min_val: float = 0.0, max_val: float = 1.0):
        """
        Initialize parameter slider.
        
        Args:
            name: Parameter name
            min_val: Minimum value
            max_val: Maximum value
        """
        super().__init__()
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        
        layout = QVBoxLayout()
        self.label = QLabel(f"{name}: {min_val:.2f}")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.valueChanged.connect(self._on_slider_change)
        
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        self.setLayout(layout)
    
    def _on_slider_change(self, value: int):
        """Handle slider value change."""
        normalized = value / 100.0
        actual = self.min_val + normalized * (self.max_val - self.min_val)
        self.label.setText(f"{self.name}: {actual:.2f}")
        self.valueChanged.emit(actual)


class PluginSelector(QWidget):
    """Widget for selecting plugins and channels."""
    
    pluginSelected = Signal(int, int)  # channel_idx, plugin_idx
    
    def __init__(self):
        """Initialize plugin selector."""
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Plugin Selector")
        layout.addWidget(label)
        self.setLayout(layout)


class TemplateSelector(QWidget):
    """Widget for selecting and configuring music task templates."""
    
    templateSelected = Signal(str, dict)  # template_name, parameters
    
    def __init__(self):
        """Initialize template selector."""
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Dropdown for template selection
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Task Template:"))
        
        self.template_combo = QComboBox()
        self.template_combo.addItem("(None - Free text)")
        self.template_combo.addItem("Design a synth sound")
        self.template_combo.addItem("Make a melody")
        self.template_combo.addItem("Recreate instrument from audio")
        self.template_combo.addItem("Remix/transform pattern")
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        
        selector_layout.addWidget(self.template_combo)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)
        
        self.setLayout(layout)
    
    def _on_template_changed(self, index: int):
        """Handle template selection change."""
        templates = {
            0: None,
            1: ("design_synth", {"style_tags": ""}),
            2: ("make_melody", {"key": "C", "scale": "major", "mood": "happy"}),
            3: ("recreate_instrument", {"timbre_analysis": {}}),
            4: ("remix_pattern", {"transformation": "humanize"})
        }
        
        template_info = templates.get(index)
        if template_info:
            template_name, params = template_info
            self.templateSelected.emit(template_name, params)
    
    def reset(self):
        """Reset to no template selected."""
        self.template_combo.setCurrentIndex(0)


class AlertBanner(QFrame):
    """Banner widget for displaying alerts and warnings."""
    
    def __init__(self, message: str = "", alert_type: str = "warning"):
        """
        Initialize alert banner.
        
        Args:
            message: Alert message text
            alert_type: Type of alert ("info", "warning", "error", "success")
        """
        super().__init__()
        self.alert_type = alert_type
        
        # Style the frame
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)
        self._update_style()
        
        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Icon/emoji
        self.icon_label = QLabel()
        layout.addWidget(self.icon_label)
        
        # Message
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)
        
        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setMaximumWidth(30)
        self.close_button.clicked.connect(self.hide)
        layout.addWidget(self.close_button)
        
        self.setLayout(layout)
        self.set_message(message, alert_type)
    
    def _update_style(self):
        """Update banner style based on alert type."""
        styles = {
            "info": ("background-color: #d1ecf1; border: 2px solid #bee5eb; color: #0c5460;", "ℹ️"),
            "warning": ("background-color: #fff3cd; border: 2px solid #ffeeba; color: #856404;", "⚠️"),
            "error": ("background-color: #f8d7da; border: 2px solid #f5c6cb; color: #721c24;", "❌"),
            "success": ("background-color: #d4edda; border: 2px solid #c3e6cb; color: #155724;", "✅")
        }
        
        style, icon = styles.get(self.alert_type, styles["info"])
        self.setStyleSheet(style)
        return icon
    
    def set_message(self, message: str, alert_type: Optional[str] = None):
        """
        Update the banner message and type.
        
        Args:
            message: New message text
            alert_type: Optional new alert type
        """
        if alert_type:
            self.alert_type = alert_type
        
        icon = self._update_style()
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.show()
    
    def show_warning(self, message: str):
        """Show a warning message."""
        self.set_message(message, "warning")
    
    def show_error(self, message: str):
        """Show an error message."""
        self.set_message(message, "error")
    
    def show_info(self, message: str):
        """Show an info message."""
        self.set_message(message, "info")
    
    def show_success(self, message: str):
        """Show a success message."""
        self.set_message(message, "success")
