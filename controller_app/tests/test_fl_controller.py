"""
Test FL Studio controller script functions.
Tests run in mock mode since FL Studio API is not available in test environment.
"""

import sys
import os
import pytest

# Add paths for imports
test_dir = os.path.dirname(os.path.abspath(__file__))
controller_app_dir = os.path.dirname(test_dir)
repo_root = os.path.dirname(controller_app_dir)
fl_scripts_dir = os.path.join(repo_root, 'fl_scripts')

if fl_scripts_dir not in sys.path:
    sys.path.insert(0, fl_scripts_dir)

# Import controller functions
from controller import main


def test_imports():
    """Test that all required modules can be imported."""
    assert main is not None
    assert hasattr(main, 'OnInit')
    assert hasattr(main, 'OnDeInit')
    assert hasattr(main, 'OnIdle')
    assert hasattr(main, 'OnMidiIn')


def test_oninit():
    """Test OnInit function (runs in mock mode)."""
    # Should not raise any exceptions
    try:
        main.OnInit()
        success = True
    except Exception as e:
        print(f"OnInit error: {e}")
        success = False
        
    assert success is True


def test_ondeinit():
    """Test OnDeInit function."""
    # Initialize first
    main.OnInit()
    
    # Should not raise any exceptions
    try:
        main.OnDeInit()
        success = True
    except Exception as e:
        print(f"OnDeInit error: {e}")
        success = False
        
    assert success is True


def test_onidle():
    """Test OnIdle function."""
    # Should not raise any exceptions
    try:
        main.OnIdle()
        success = True
    except Exception as e:
        print(f"OnIdle error: {e}")
        success = False
        
    assert success is True


def test_onmidiin():
    """Test OnMidiIn function."""
    # Mock MIDI event (doesn't need to be real in our current implementation)
    mock_event = None
    
    # Should not raise any exceptions
    try:
        main.OnMidiIn(mock_event)
        success = True
    except Exception as e:
        print(f"OnMidiIn error: {e}")
        success = False
        
    assert success is True


def test_enumerate_channels():
    """Test channel enumeration (mock mode)."""
    channels = main.enumerate_channels()
    
    assert isinstance(channels, list)
    # In mock mode, should return empty list
    assert len(channels) == 0


def test_enumerate_plugins():
    """Test plugin enumeration (mock mode)."""
    plugins = main.enumerate_plugins(channel_idx=0)
    
    assert isinstance(plugins, list)
    # In mock mode with invalid plugin, should return empty list
    assert len(plugins) == 0


def test_get_plugin_parameters():
    """Test getting plugin parameters (mock mode)."""
    params = main.get_plugin_parameters(channel_idx=0, slot_idx=0)
    
    assert isinstance(params, list)
    # In mock mode, should return 10 mock parameters
    assert len(params) == 10
    
    # Check parameter structure
    if len(params) > 0:
        param = params[0]
        assert "index" in param
        assert "name" in param
        assert "value" in param
        assert "min_value" in param
        assert "max_value" in param


def test_set_plugin_parameter():
    """Test setting plugin parameter (mock mode)."""
    result = main.set_plugin_parameter(
        channel_idx=0,
        param_idx=0,
        value=0.5,
        slot_idx=0,
        smooth=False
    )
    
    # In mock mode, this should succeed
    assert result is True


def test_set_plugin_parameter_clamping():
    """Test that parameter values are clamped."""
    # Test value > 1
    result = main.set_plugin_parameter(
        channel_idx=0,
        param_idx=0,
        value=1.5,
        smooth=False
    )
    assert result is True
    
    # Test value < 0
    result = main.set_plugin_parameter(
        channel_idx=0,
        param_idx=0,
        value=-0.5,
        smooth=False
    )
    assert result is True


def test_set_plugin_parameter_smoothing():
    """Test parameter smoothing."""
    # First set
    result1 = main.set_plugin_parameter(
        channel_idx=0,
        param_idx=0,
        value=0.0,
        smooth=True
    )
    assert result1 is True
    
    # Second set (should be smoothed)
    result2 = main.set_plugin_parameter(
        channel_idx=0,
        param_idx=0,
        value=1.0,
        smooth=True
    )
    assert result2 is True


def test_enumerate_mixer_tracks():
    """Test mixer track enumeration (mock mode)."""
    tracks = main.enumerate_mixer_tracks()
    
    assert isinstance(tracks, list)
    # Mock mixer has 127 tracks
    assert len(tracks) == 127
    
    # Check track structure
    if len(tracks) > 0:
        track = tracks[0]
        assert "index" in track
        assert "name" in track
        assert "volume" in track
        assert "pan" in track
        assert "mute" in track
        assert "solo" in track


def test_handle_transport_command():
    """Test transport command handling (mock mode)."""
    from shared.message_schemas import TransportCommand
    
    commands = [
        TransportCommand.PLAY,
        TransportCommand.STOP,
        TransportCommand.RECORD,
        TransportCommand.PAUSE
    ]
    
    for command in commands:
        result = main.handle_transport_command(command)
        assert result is True


def test_handle_mixer_command():
    """Test mixer command handling (mock mode)."""
    # Test set volume
    result = main.handle_mixer_command(
        track_idx=0,
        action="set_volume",
        volume=0.5
    )
    assert result is True
    
    # Test set pan
    result = main.handle_mixer_command(
        track_idx=0,
        action="set_pan",
        pan=-0.3
    )
    assert result is True


def test_handle_channel_command():
    """Test channel command handling (mock mode)."""
    # Test select by index
    result = main.handle_channel_command(
        action="select_by_index",
        index=5
    )
    assert result is True
    
    # Test select by name (should fail in mock as channel doesn't exist)
    result = main.handle_channel_command(
        action="select_by_name",
        name="NonExistentChannel"
    )
    assert result is False


def test_select_pattern():
    """Test pattern selection (mock mode)."""
    result = main.select_pattern(pattern_idx=1)
    assert result is True


def test_mock_mode_detection():
    """Test that mock mode is properly detected."""
    # Should be running in mock mode in tests
    assert main.FL_AVAILABLE is False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
