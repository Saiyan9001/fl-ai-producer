#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reusable UI components for FL-AI-Producer
"""
from PySide6.QtWidgets import QWidget, QPushButton, QSlider, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal, Qt


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
