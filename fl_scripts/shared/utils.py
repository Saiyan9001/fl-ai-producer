"""
Utility functions for FL Studio IPC communication.
Includes parameter scaling, smoothing, and value conversions.
"""

import math
from typing import Dict, Optional


class ValueScaler:
    """
    Handles scaling between normalized (0-1) and plugin-specific value ranges.
    """
    
    @staticmethod
    def normalize(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        Normalize a value from a specific range to 0-1.
        
        Args:
            value: Value to normalize
            min_val: Minimum value of the range
            max_val: Maximum value of the range
            
        Returns:
            Normalized value (0-1)
        """
        if max_val == min_val:
            return 0.0
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    
    @staticmethod
    def denormalize(normalized: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        Convert a normalized (0-1) value to a specific range.
        
        Args:
            normalized: Normalized value (0-1)
            min_val: Minimum value of the target range
            max_val: Maximum value of the target range
            
        Returns:
            Denormalized value
        """
        clamped = max(0.0, min(1.0, normalized))
        return min_val + clamped * (max_val - min_val)
    
    @staticmethod
    def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        Clamp a value to a specific range.
        
        Args:
            value: Value to clamp
            min_val: Minimum value
            max_val: Maximum value
            
        Returns:
            Clamped value
        """
        return max(min_val, min(max_val, value))


class ExponentialMovingAverage:
    """
    Exponential Moving Average for smoothing parameter changes.
    Helps avoid zipper noise when changing parameters.
    """
    
    def __init__(self, alpha: float = 0.3):
        """
        Initialize the EMA.
        
        Args:
            alpha: Smoothing factor (0-1). Higher = less smoothing, more responsive.
        """
        self.alpha = max(0.0, min(1.0, alpha))
        self.values: Dict[str, float] = {}
    
    def update(self, key: str, new_value: float, force: bool = False) -> float:
        """
        Update and smooth a value.
        
        Args:
            key: Key identifier for the value
            new_value: New value to smooth
            force: If True, set the value directly without smoothing
            
        Returns:
            Smoothed value
        """
        if force or key not in self.values:
            self.values[key] = new_value
            return new_value
        
        old_value = self.values[key]
        smoothed = self.alpha * new_value + (1.0 - self.alpha) * old_value
        self.values[key] = smoothed
        return smoothed
    
    def get(self, key: str, default: float = 0.0) -> float:
        """
        Get the current smoothed value.
        
        Args:
            key: Key identifier
            default: Default value if key not found
            
        Returns:
            Current smoothed value
        """
        return self.values.get(key, default)
    
    def reset(self, key: Optional[str] = None):
        """
        Reset smoothed values.
        
        Args:
            key: Specific key to reset, or None to reset all
        """
        if key is None:
            self.values.clear()
        elif key in self.values:
            del self.values[key]


def db_to_linear(db: float) -> float:
    """
    Convert decibels to linear scale.
    
    Args:
        db: Value in decibels
        
    Returns:
        Linear value
    """
    return math.pow(10.0, db / 20.0)


def linear_to_db(linear: float, min_db: float = -80.0) -> float:
    """
    Convert linear scale to decibels.
    
    Args:
        linear: Linear value
        min_db: Minimum dB value (for values near zero)
        
    Returns:
        Value in decibels
    """
    if linear <= 0.0:
        return min_db
    return 20.0 * math.log10(linear)


def interpolate(value_a: float, value_b: float, t: float) -> float:
    """
    Linear interpolation between two values.
    
    Args:
        value_a: Start value
        value_b: End value
        t: Interpolation factor (0-1)
        
    Returns:
        Interpolated value
    """
    t = max(0.0, min(1.0, t))
    return value_a + (value_b - value_a) * t


def snap_to_discrete(value: float, num_steps: int) -> float:
    """
    Snap a continuous value to discrete steps.
    
    Args:
        value: Value to snap (0-1)
        num_steps: Number of discrete steps
        
    Returns:
        Snapped value
    """
    if num_steps <= 1:
        return value
    step = 1.0 / (num_steps - 1)
    step_index = round(value / step)
    return step_index * step


def format_param_value(value: float, is_percentage: bool = False, 
                      decimal_places: int = 2) -> str:
    """
    Format a parameter value for display.
    
    Args:
        value: Value to format (0-1)
        is_percentage: If True, format as percentage
        decimal_places: Number of decimal places
        
    Returns:
        Formatted string
    """
    if is_percentage:
        return f"{value * 100:.{decimal_places}f}%"
    return f"{value:.{decimal_places}f}"
