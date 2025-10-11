"""
Test shared utilities (scaling, smoothing, etc.)
"""

import sys
import os
import pytest
import math

# Add paths for imports
test_dir = os.path.dirname(os.path.abspath(__file__))
controller_app_dir = os.path.dirname(test_dir)
repo_root = os.path.dirname(controller_app_dir)
fl_scripts_dir = os.path.join(repo_root, 'fl_scripts')

if fl_scripts_dir not in sys.path:
    sys.path.insert(0, fl_scripts_dir)

from shared.utils import (
    ValueScaler, ExponentialMovingAverage,
    db_to_linear, linear_to_db, interpolate,
    snap_to_discrete, format_param_value
)


class TestValueScaler:
    """Test ValueScaler class."""
    
    def test_normalize(self):
        """Test value normalization."""
        # Test basic normalization
        assert ValueScaler.normalize(50, 0, 100) == 0.5
        assert ValueScaler.normalize(0, 0, 100) == 0.0
        assert ValueScaler.normalize(100, 0, 100) == 1.0
        
        # Test different range
        assert ValueScaler.normalize(5, 0, 10) == 0.5
        
        # Test with negative range
        result = ValueScaler.normalize(0, -10, 10)
        assert abs(result - 0.5) < 0.001
    
    def test_normalize_clipping(self):
        """Test that normalize clips to 0-1."""
        # Values outside range should be clipped
        assert ValueScaler.normalize(150, 0, 100) == 1.0
        assert ValueScaler.normalize(-50, 0, 100) == 0.0
    
    def test_normalize_zero_range(self):
        """Test normalize with zero range."""
        # Should return 0 to avoid division by zero
        assert ValueScaler.normalize(5, 5, 5) == 0.0
    
    def test_denormalize(self):
        """Test value denormalization."""
        # Test basic denormalization
        assert ValueScaler.denormalize(0.5, 0, 100) == 50.0
        assert ValueScaler.denormalize(0.0, 0, 100) == 0.0
        assert ValueScaler.denormalize(1.0, 0, 100) == 100.0
        
        # Test different range
        assert ValueScaler.denormalize(0.25, 0, 10) == 2.5
    
    def test_denormalize_clipping(self):
        """Test that denormalize clips input to 0-1."""
        # Input outside 0-1 should be clipped
        assert ValueScaler.denormalize(1.5, 0, 100) == 100.0
        assert ValueScaler.denormalize(-0.5, 0, 100) == 0.0
    
    def test_clamp(self):
        """Test value clamping."""
        assert ValueScaler.clamp(0.5, 0, 1) == 0.5
        assert ValueScaler.clamp(1.5, 0, 1) == 1.0
        assert ValueScaler.clamp(-0.5, 0, 1) == 0.0
        
        # Test different range
        assert ValueScaler.clamp(150, 0, 100) == 100
        assert ValueScaler.clamp(-50, 0, 100) == 0
    
    def test_normalize_denormalize_roundtrip(self):
        """Test that normalize and denormalize are inverses."""
        original = 75.0
        normalized = ValueScaler.normalize(original, 0, 100)
        denormalized = ValueScaler.denormalize(normalized, 0, 100)
        assert abs(denormalized - original) < 0.001


class TestExponentialMovingAverage:
    """Test ExponentialMovingAverage class."""
    
    def test_initialization(self):
        """Test EMA initialization."""
        ema = ExponentialMovingAverage(alpha=0.5)
        assert ema.alpha == 0.5
        assert len(ema.values) == 0
    
    def test_alpha_clamping(self):
        """Test that alpha is clamped to 0-1."""
        ema1 = ExponentialMovingAverage(alpha=1.5)
        assert ema1.alpha == 1.0
        
        ema2 = ExponentialMovingAverage(alpha=-0.5)
        assert ema2.alpha == 0.0
    
    def test_first_update(self):
        """Test that first update sets value directly."""
        ema = ExponentialMovingAverage(alpha=0.3)
        result = ema.update("key1", 1.0)
        assert result == 1.0
        assert ema.get("key1") == 1.0
    
    def test_smoothing(self):
        """Test that subsequent updates are smoothed."""
        ema = ExponentialMovingAverage(alpha=0.3)
        
        # First update
        ema.update("key1", 0.0)
        
        # Second update should be smoothed
        # Expected: 0.3 * 1.0 + 0.7 * 0.0 = 0.3
        result = ema.update("key1", 1.0)
        assert abs(result - 0.3) < 0.001
    
    def test_multiple_keys(self):
        """Test that EMA tracks multiple keys independently."""
        ema = ExponentialMovingAverage(alpha=0.5)
        
        ema.update("key1", 0.0)
        ema.update("key2", 1.0)
        
        assert ema.get("key1") == 0.0
        assert ema.get("key2") == 1.0
    
    def test_force_update(self):
        """Test force update bypasses smoothing."""
        ema = ExponentialMovingAverage(alpha=0.3)
        
        ema.update("key1", 0.0)
        result = ema.update("key1", 1.0, force=True)
        
        # Should set to 1.0 directly, not smoothed
        assert result == 1.0
        assert ema.get("key1") == 1.0
    
    def test_get_default(self):
        """Test get with default value."""
        ema = ExponentialMovingAverage()
        assert ema.get("nonexistent", 0.5) == 0.5
    
    def test_reset_specific_key(self):
        """Test resetting a specific key."""
        ema = ExponentialMovingAverage()
        
        ema.update("key1", 1.0)
        ema.update("key2", 2.0)
        
        ema.reset("key1")
        
        assert ema.get("key1", 0.0) == 0.0
        assert ema.get("key2") == 2.0
    
    def test_reset_all(self):
        """Test resetting all keys."""
        ema = ExponentialMovingAverage()
        
        ema.update("key1", 1.0)
        ema.update("key2", 2.0)
        
        ema.reset()
        
        assert len(ema.values) == 0


class TestConversionFunctions:
    """Test conversion utility functions."""
    
    def test_db_to_linear(self):
        """Test dB to linear conversion."""
        # 0 dB = 1.0 linear
        assert abs(db_to_linear(0.0) - 1.0) < 0.001
        
        # -6 dB ≈ 0.5 linear
        assert abs(db_to_linear(-6.0) - 0.5) < 0.01
        
        # -20 dB ≈ 0.1 linear
        assert abs(db_to_linear(-20.0) - 0.1) < 0.001
    
    def test_linear_to_db(self):
        """Test linear to dB conversion."""
        # 1.0 linear = 0 dB
        assert abs(linear_to_db(1.0) - 0.0) < 0.001
        
        # 0.5 linear ≈ -6 dB
        assert abs(linear_to_db(0.5) - (-6.0)) < 0.1
        
        # 0.0 linear = min_db
        assert linear_to_db(0.0, min_db=-80.0) == -80.0
    
    def test_db_linear_roundtrip(self):
        """Test that dB and linear conversions are inverses."""
        linear = 0.7
        db = linear_to_db(linear)
        back_to_linear = db_to_linear(db)
        assert abs(back_to_linear - linear) < 0.001
    
    def test_interpolate(self):
        """Test linear interpolation."""
        assert interpolate(0.0, 1.0, 0.0) == 0.0
        assert interpolate(0.0, 1.0, 1.0) == 1.0
        assert interpolate(0.0, 1.0, 0.5) == 0.5
        
        # Test with different values
        assert interpolate(10.0, 20.0, 0.5) == 15.0
    
    def test_interpolate_clamping(self):
        """Test that interpolate clamps t to 0-1."""
        assert interpolate(0.0, 1.0, -0.5) == 0.0
        assert interpolate(0.0, 1.0, 1.5) == 1.0
    
    def test_snap_to_discrete(self):
        """Test snapping to discrete steps."""
        # 3 steps: 0.0, 0.5, 1.0
        assert snap_to_discrete(0.0, 3) == 0.0
        assert snap_to_discrete(0.5, 3) == 0.5
        assert snap_to_discrete(1.0, 3) == 1.0
        
        # Values between steps
        assert abs(snap_to_discrete(0.25, 3) - 0.0) < 0.001  # Closer to 0
        assert abs(snap_to_discrete(0.75, 3) - 1.0) < 0.001  # Closer to 1
    
    def test_snap_to_discrete_edge_cases(self):
        """Test snap_to_discrete edge cases."""
        # 1 step (should just return value)
        assert snap_to_discrete(0.7, 1) == 0.7
        
        # 0 or negative steps
        assert snap_to_discrete(0.5, 0) == 0.5
    
    def test_format_param_value(self):
        """Test parameter value formatting."""
        # Normal format
        assert format_param_value(0.5, is_percentage=False, decimal_places=2) == "0.50"
        
        # Percentage format
        assert format_param_value(0.5, is_percentage=True, decimal_places=2) == "50.00%"
        
        # Different decimal places
        assert format_param_value(0.333, is_percentage=False, decimal_places=3) == "0.333"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
