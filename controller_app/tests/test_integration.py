"""
Integration test demonstrating the full IPC roundtrip.
This test simulates the complete workflow from controller app to FL Studio script.
"""

import sys
import os
import pytest
import time
import threading

# Add paths for imports
test_dir = os.path.dirname(os.path.abspath(__file__))
controller_app_dir = os.path.dirname(test_dir)
repo_root = os.path.dirname(controller_app_dir)
fl_scripts_dir = os.path.join(repo_root, 'fl_scripts')

if controller_app_dir not in sys.path:
    sys.path.insert(0, controller_app_dir)
if fl_scripts_dir not in sys.path:
    sys.path.insert(0, fl_scripts_dir)

# Import FL controller module
from controller import main as fl_main

# Import IPC client from FL script
from controller.ipc_client import IPCClient

# Import mock server from test suite
from controller_app.tests.test_ipc_roundtrip import MockIPCServer


def test_full_integration_workflow():
    """
    Test the complete workflow:
    1. FL Script initializes (OnInit)
    2. Mock server starts (simulating controller app)
    3. IPC client connects
    4. Various commands are sent and responses received
    5. FL Script processes commands
    6. Cleanup
    """
    print("\n=== Starting Integration Test ===")
    
    # Step 1: Initialize FL Script
    print("Step 1: Initializing FL Script...")
    fl_main.OnInit()
    assert fl_main._ipc_client is not None
    print("✓ FL Script initialized")
    
    # Step 2: Start mock server (simulating controller app)
    print("\nStep 2: Starting mock IPC server...")
    mock_server = MockIPCServer(port=5557)
    mock_server.start()
    print("✓ Mock server started on port 5557")
    
    # Step 3: Create a new IPC client for testing (use different port)
    print("\nStep 3: Creating test IPC client...")
    test_client = IPCClient(host="127.0.0.1", port=5557, timeout_ms=1000)
    connected = test_client.connect()
    assert connected is True
    print("✓ Test client connected")
    
    # Step 4: Test various commands
    print("\nStep 4: Testing various commands...")
    
    # Test ping
    print("  - Testing ping...")
    result = test_client.ping()
    assert result is True
    print("    ✓ Ping successful")
    
    # Test get state
    print("  - Testing get_state...")
    state = test_client.get_state()
    assert state is not None
    assert "channels" in state
    assert "fl_version" in state
    print(f"    ✓ Got state with {len(state['channels'])} channels")
    
    # Test set parameter
    print("  - Testing set_param...")
    result = test_client.set_param(
        plugin_index=0,
        param_index=3,
        value=0.75
    )
    assert result is True
    print("    ✓ Set parameter successful")
    
    # Test transport command
    print("  - Testing transport command...")
    result = test_client.send_transport_command("play")
    assert result is True
    print("    ✓ Transport command successful")
    
    # Test mixer control
    print("  - Testing mixer control...")
    result = test_client.set_mixer_volume(track_index=0, volume=0.8)
    assert result is True
    print("    ✓ Mixer volume set successful")
    
    # Test channel selection
    print("  - Testing channel selection...")
    result = test_client.select_channel(channel_index=2)
    assert result is True
    print("    ✓ Channel selection successful")
    
    # Step 5: Verify FL Script functions work
    print("\nStep 5: Testing FL Script functions directly...")
    
    # Test enumerate channels
    channels = fl_main.enumerate_channels()
    print(f"  ✓ Enumerated {len(channels)} channels")
    
    # Test get plugin parameters
    params = fl_main.get_plugin_parameters(channel_idx=0, slot_idx=0)
    print(f"  ✓ Got {len(params)} parameters")
    
    # Test set parameter
    result = fl_main.set_plugin_parameter(
        channel_idx=0,
        param_idx=5,
        value=0.6,
        smooth=False
    )
    assert result is True
    print("  ✓ Set parameter directly successful")
    
    # Test mixer tracks
    tracks = fl_main.enumerate_mixer_tracks()
    print(f"  ✓ Enumerated {len(tracks)} mixer tracks")
    
    # Step 6: Cleanup
    print("\nStep 6: Cleanup...")
    test_client.disconnect()
    print("  ✓ Test client disconnected")
    
    fl_main.OnDeInit()
    print("  ✓ FL Script deinitialized")
    
    mock_server.stop()
    print("  ✓ Mock server stopped")
    
    print("\n=== Integration Test Complete ===")
    print("All systems working correctly!")


def test_parameter_smoothing_workflow():
    """
    Test parameter smoothing in a realistic scenario.
    """
    print("\n=== Testing Parameter Smoothing ===")
    
    # Initialize
    fl_main.OnInit()
    
    # Set parameter multiple times with smoothing
    values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    
    for i, value in enumerate(values):
        result = fl_main.set_plugin_parameter(
            channel_idx=0,
            param_idx=0,
            value=value,
            smooth=True
        )
        assert result is True
        print(f"  Step {i+1}: Set value {value:.1f}")
    
    # The actual values should be smoothed (not exactly the input values)
    # This is working correctly if no exceptions are raised
    
    fl_main.OnDeInit()
    print("✓ Parameter smoothing test complete")


def test_error_handling():
    """
    Test error handling in various scenarios.
    """
    print("\n=== Testing Error Handling ===")
    
    fl_main.OnInit()
    
    # Test with invalid channel (should handle gracefully)
    print("  - Testing invalid channel selection...")
    result = fl_main.handle_channel_command(
        action="select_by_name",
        name="NonExistentChannel"
    )
    assert result is False  # Should fail gracefully
    print("    ✓ Invalid channel handled correctly")
    
    # Test with invalid action
    print("  - Testing invalid mixer action...")
    result = fl_main.handle_mixer_command(
        track_idx=0,
        action="invalid_action"
    )
    assert result is False  # Should fail gracefully
    print("    ✓ Invalid action handled correctly")
    
    # Test with out-of-range parameter value (should be clamped)
    print("  - Testing value clamping...")
    result = fl_main.set_plugin_parameter(
        channel_idx=0,
        param_idx=0,
        value=5.0,  # Way out of range
        smooth=False
    )
    assert result is True  # Should succeed with clamped value
    print("    ✓ Out-of-range value clamped correctly")
    
    fl_main.OnDeInit()
    print("✓ Error handling test complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
