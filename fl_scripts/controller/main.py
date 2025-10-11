"""
FL Studio MIDI Controller Script - Main Entry Point
Provides integration between FL Studio and the controller app via IPC.
"""

import sys
import os
import uuid
from typing import Optional, Dict, Any, List

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Try to import FL Studio modules
try:
    import channels
    import mixer
    import plugins
    import transport
    import patterns
    import general
    import midi
    FL_AVAILABLE = True
except ImportError:
    FL_AVAILABLE = False
    print("FL Studio API not available - running in mock mode")

# Import our modules
from controller.ipc_client import IPCClient
from shared.message_schemas import (
    MessageType, TransportCommand, create_message, create_response,
    create_state_snapshot, create_plugin_param, create_channel_info,
    create_mixer_track_info
)
from shared.utils import ValueScaler, ExponentialMovingAverage


# Global state
_ipc_client: Optional[IPCClient] = None
_smoother = ExponentialMovingAverage(alpha=0.3)
_fl_version = "Unknown"
_last_selected_channel = -1


# Mock implementations for when FL API is not available
class MockChannels:
    @staticmethod
    def channelCount(): return 0
    @staticmethod
    def getChannelName(idx): return f"Channel {idx}"
    @staticmethod
    def selectedChannel(): return 0
    @staticmethod
    def selectOneChannel(idx): pass
    @staticmethod
    def getChannelColor(idx): return 0

class MockMixer:
    @staticmethod
    def trackCount(): return 127
    @staticmethod
    def getTrackName(idx): return f"Track {idx}"
    @staticmethod
    def getTrackVolume(idx): return 0.8
    @staticmethod
    def setTrackVolume(idx, vol): pass
    @staticmethod
    def getTrackPan(idx): return 0.0
    @staticmethod
    def setTrackPan(idx, pan): pass
    @staticmethod
    def isTrackMuted(idx): return False
    @staticmethod
    def isTrackSolo(idx): return False

class MockPlugins:
    @staticmethod
    def getPluginName(chan_idx, slot_idx): return "Mock Plugin"
    @staticmethod
    def getParamName(param_idx, chan_idx, slot_idx): return f"Param {param_idx}"
    @staticmethod
    def getParamValue(param_idx, chan_idx, slot_idx): return 0.5
    @staticmethod
    def setParamValue(value, param_idx, chan_idx, slot_idx): pass
    @staticmethod
    def getParamCount(chan_idx, slot_idx): return 10
    @staticmethod
    def isValid(chan_idx, slot_idx): return True

class MockTransport:
    @staticmethod
    def start(): pass
    @staticmethod
    def stop(): pass
    @staticmethod
    def record(): pass
    @staticmethod
    def isPlaying(): return False
    @staticmethod
    def isRecording(): return False

class MockPatterns:
    @staticmethod
    def patternCount(): return 1
    @staticmethod
    def getPatternName(idx): return f"Pattern {idx}"
    @staticmethod
    def jumpToPattern(idx): pass

class MockGeneral:
    @staticmethod
    def getVersion(): return (21, 2, 0, 0)

class MockMidi:
    # MIDI constants
    FPN_Param = 0

# Use mock if FL not available
if not FL_AVAILABLE:
    channels = MockChannels()
    mixer = MockMixer()
    plugins = MockPlugins()
    transport = MockTransport()
    patterns = MockPatterns()
    general = MockGeneral()
    
    # Create a mock midi module with constants
    class _MockMidi:
        FPN_Param = 0
    midi = _MockMidi()


def OnInit():
    """
    Called when FL Studio initializes the script.
    Set up IPC client and detect FL version.
    """
    global _ipc_client, _fl_version
    
    print("=" * 60)
    print("FL-AI-Producer Controller Script Initializing...")
    print("=" * 60)
    
    # Detect FL Studio version
    try:
        if FL_AVAILABLE:
            version_tuple = general.getVersion()
            _fl_version = f"FL Studio {version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
            print(f"FL Studio Version: {_fl_version}")
        else:
            _fl_version = "Mock Mode"
            print("Running in MOCK MODE (FL Studio API not available)")
    except Exception as e:
        _fl_version = "Unknown"
        print(f"Could not detect FL version: {e}")
    
    # Initialize IPC client (non-blocking)
    try:
        _ipc_client = IPCClient(host="127.0.0.1", port=5555, timeout_ms=1000)
        print("IPC client created")
        
        # Try initial connection (non-blocking, will retry in background)
        if _ipc_client.connect():
            print("Successfully connected to controller app")
            # Send initial ping
            if _ipc_client.ping():
                print("Ping successful")
        else:
            print("Initial connection failed - will retry on first message")
            
    except Exception as e:
        print(f"Error initializing IPC client: {e}")
        _ipc_client = None
    
    print("Initialization complete")
    print("=" * 60)


def OnDeInit():
    """
    Called when FL Studio closes or unloads the script.
    Clean up resources.
    """
    global _ipc_client
    
    print("FL-AI-Producer Controller Script shutting down...")
    
    if _ipc_client:
        try:
            _ipc_client.disconnect()
            print("IPC client disconnected")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    print("Shutdown complete")


def OnIdle():
    """
    Called periodically when FL Studio is idle.
    Can be used for periodic state updates or maintenance.
    """
    # This is called very frequently, so we keep it lightweight
    # Could add periodic state sync here if needed
    pass


def OnMidiIn(event):
    """
    Called when MIDI input is received.
    We can use this to trigger custom actions if needed.
    
    Args:
        event: MIDI event object
    """
    # For now, we don't process MIDI input
    # This could be extended to allow MIDI control of the script
    pass


def enumerate_channels() -> List[Dict[str, Any]]:
    """
    Enumerate all channels in the current FL Studio project.
    
    Returns:
        List of channel dictionaries
    """
    channel_list = []
    
    try:
        channel_count = channels.channelCount()
        
        for i in range(channel_count):
            try:
                name = channels.getChannelName(i)
                channel_info = create_channel_info(
                    index=i,
                    name=name,
                    plugin_index=None,  # Could be extended to detect plugin slot
                    plugin_name=None
                )
                channel_list.append(channel_info)
            except Exception as e:
                print(f"Error getting channel {i}: {e}")
                
    except Exception as e:
        print(f"Error enumerating channels: {e}")
    
    return channel_list


def enumerate_plugins(channel_idx: int) -> List[Dict[str, Any]]:
    """
    Enumerate plugins on a specific channel.
    
    Args:
        channel_idx: Channel index
        
    Returns:
        List of plugin dictionaries
    """
    plugin_list = []
    
    try:
        # FL Studio has multiple plugin slots per channel
        # Typically slot 0 is the main generator plugin
        for slot_idx in range(10):  # Check first 10 slots
            try:
                if plugins.isValid(channel_idx, slot_idx):
                    plugin_name = plugins.getPluginName(channel_idx, slot_idx)
                    plugin_list.append({
                        "index": slot_idx,
                        "name": plugin_name,
                        "channel_index": channel_idx
                    })
            except:
                # Slot not valid or error, continue
                pass
                
    except Exception as e:
        print(f"Error enumerating plugins for channel {channel_idx}: {e}")
    
    return plugin_list


def get_plugin_parameters(channel_idx: int, slot_idx: int = 0) -> List[Dict[str, Any]]:
    """
    Get all parameters for a plugin.
    
    Args:
        channel_idx: Channel index
        slot_idx: Plugin slot index
        
    Returns:
        List of parameter dictionaries
    """
    param_list = []
    
    try:
        if not plugins.isValid(channel_idx, slot_idx):
            return param_list
        
        param_count = plugins.getParamCount(channel_idx, slot_idx)
        
        for param_idx in range(param_count):
            try:
                # Get parameter name using FPN_Param flag
                param_name = plugins.getParamName(param_idx, channel_idx, slot_idx)
                if not param_name:
                    param_name = f"Parameter {param_idx}"
                
                # Get current value (already normalized 0-1 in FL Studio)
                param_value = plugins.getParamValue(param_idx, channel_idx, slot_idx)
                
                param_info = create_plugin_param(
                    index=param_idx,
                    name=param_name,
                    value=param_value,
                    min_value=0.0,
                    max_value=1.0
                )
                param_list.append(param_info)
                
            except Exception as e:
                print(f"Error getting parameter {param_idx}: {e}")
                
    except Exception as e:
        print(f"Error getting plugin parameters: {e}")
    
    return param_list


def set_plugin_parameter(channel_idx: int, param_idx: int, value: float, 
                        slot_idx: int = 0, smooth: bool = True) -> bool:
    """
    Set a plugin parameter value.
    
    Args:
        channel_idx: Channel index
        param_idx: Parameter index
        value: Normalized value (0-1)
        slot_idx: Plugin slot index
        smooth: Apply smoothing to avoid zipper noise
        
    Returns:
        True if successful
    """
    try:
        if not plugins.isValid(channel_idx, slot_idx):
            print(f"Plugin not valid at channel {channel_idx}, slot {slot_idx}")
            return False
        
        # Clamp value
        value = ValueScaler.clamp(value, 0.0, 1.0)
        
        # Apply smoothing if enabled
        if smooth:
            key = f"{channel_idx}_{slot_idx}_{param_idx}"
            value = _smoother.update(key, value)
        
        # Set parameter value
        plugins.setParamValue(value, param_idx, channel_idx, slot_idx)
        return True
        
    except Exception as e:
        print(f"Error setting parameter: {e}")
        return False


def enumerate_mixer_tracks() -> List[Dict[str, Any]]:
    """
    Enumerate all mixer tracks.
    
    Returns:
        List of mixer track dictionaries
    """
    mixer_list = []
    
    try:
        track_count = mixer.trackCount()
        
        for i in range(track_count):
            try:
                name = mixer.getTrackName(i)
                volume = mixer.getTrackVolume(i)
                pan = mixer.getTrackPan(i)
                mute = mixer.isTrackMuted(i)
                solo = mixer.isTrackSolo(i)
                
                track_info = create_mixer_track_info(
                    index=i,
                    name=name if name else f"Track {i}",
                    volume=volume,
                    pan=pan,
                    mute=mute,
                    solo=solo
                )
                mixer_list.append(track_info)
                
            except Exception as e:
                print(f"Error getting mixer track {i}: {e}")
                
    except Exception as e:
        print(f"Error enumerating mixer tracks: {e}")
    
    return mixer_list


def handle_transport_command(command: str) -> bool:
    """
    Handle a transport command.
    
    Args:
        command: Transport command string
        
    Returns:
        True if successful
    """
    try:
        if command == TransportCommand.PLAY:
            transport.start()
        elif command == TransportCommand.STOP:
            transport.stop()
        elif command == TransportCommand.RECORD:
            transport.record()
        elif command == TransportCommand.PAUSE:
            # FL doesn't have a separate pause, so we stop
            transport.stop()
        else:
            print(f"Unknown transport command: {command}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error handling transport command: {e}")
        return False


def handle_mixer_command(track_idx: int, action: str, **kwargs) -> bool:
    """
    Handle a mixer command.
    
    Args:
        track_idx: Mixer track index
        action: Action to perform
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    try:
        if action == "set_volume":
            volume = kwargs.get("volume", 0.8)
            volume = ValueScaler.clamp(volume, 0.0, 1.0)
            mixer.setTrackVolume(track_idx, volume)
            
        elif action == "set_pan":
            pan = kwargs.get("pan", 0.0)
            pan = ValueScaler.clamp(pan, -1.0, 1.0)
            mixer.setTrackPan(track_idx, pan)
            
        else:
            print(f"Unknown mixer action: {action}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error handling mixer command: {e}")
        return False


def handle_channel_command(action: str, **kwargs) -> bool:
    """
    Handle a channel selection command.
    
    Args:
        action: Action to perform
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    global _last_selected_channel
    
    try:
        if action == "select_by_index":
            channel_idx = kwargs.get("index", 0)
            channels.selectOneChannel(channel_idx)
            _last_selected_channel = channel_idx
            
        elif action == "select_by_name":
            name = kwargs.get("name", "")
            # Search for channel by name
            channel_count = channels.channelCount()
            for i in range(channel_count):
                if channels.getChannelName(i) == name:
                    channels.selectOneChannel(i)
                    _last_selected_channel = i
                    return True
            
            print(f"Channel not found: {name}")
            return False
        
        else:
            print(f"Unknown channel action: {action}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error handling channel command: {e}")
        return False


def select_pattern(pattern_idx: int) -> bool:
    """
    Select a pattern.
    
    Args:
        pattern_idx: Pattern index
        
    Returns:
        True if successful
    """
    try:
        patterns.jumpToPattern(pattern_idx)
        return True
    except Exception as e:
        print(f"Error selecting pattern: {e}")
        return False


# Export functions that can be called by other scripts or for testing
__all__ = [
    'OnInit',
    'OnDeInit', 
    'OnIdle',
    'OnMidiIn',
    'enumerate_channels',
    'enumerate_plugins',
    'get_plugin_parameters',
    'set_plugin_parameter',
    'enumerate_mixer_tracks',
    'handle_transport_command',
    'handle_mixer_command',
    'handle_channel_command',
    'select_pattern'
]
