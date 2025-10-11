# FL-AI-Producer Controller Script - Installation & Usage

## Overview

This MIDI controller script integrates FL Studio with the FL-AI-Producer controller app via ZeroMQ IPC. It enables real-time control of plugins, mixer, transport, and channels from the desktop application.

## Requirements

- FL Studio 21.2 or later (earlier versions may work but are untested)
- Python 3.11+ (embedded with FL Studio or system Python)
- PyZMQ (`pip install pyzmq`)

## Installation

### Step 1: Install PyZMQ in FL Studio's Python Environment

FL Studio uses its own Python environment. You need to install PyZMQ there:

**Option A: Using FL Studio's Python (Windows)**
```bash
# Navigate to FL Studio's Python directory (adjust path as needed)
cd "C:\Program Files\Image-Line\FL Studio 21\Python"

# Install PyZMQ
python.exe -m pip install pyzmq
```

**Option B: Using System Python**
If FL Studio is configured to use your system Python:
```bash
pip install pyzmq
```

### Step 2: Copy Script Files to FL Studio

Copy the entire `controller` folder to FL Studio's user scripts directory:

**Windows Default Path:**
```
C:\Users\<YourUsername>\Documents\Image-Line\FL Studio\Settings\Hardware\<controller-folder-name>
```

The structure should look like:
```
FL Studio\Settings\Hardware\FL-AI-Producer\
├── main.py
├── ipc_client.py
├── device_Definition.py
└── __init__.py
```

**Also copy the shared folder:**
```
FL Studio\Settings\Hardware\shared\
├── message_schemas.py
├── utils.py
└── __init__.py
```

Or place it one level up so both controller and pianoroll scripts can access it.

### Step 3: Enable the Script in FL Studio

1. Open FL Studio
2. Go to **Options → MIDI Settings** (or press F10)
3. In the **Input** section, find an empty slot
4. Click the device dropdown and select **FL-AI-Producer**
5. Enable the device by checking the **Enable** box
6. Set the port to **0** (or leave as default)
7. Click **Apply** or **OK**

### Step 4: Verify Installation

1. Open the **Script output** window: **View → Script Output** (or Shift+F12)
2. Look for initialization messages:
   ```
   ============================================================
   FL-AI-Producer Controller Script Initializing...
   ============================================================
   FL Studio Version: FL Studio 21.2.x
   IPC client created
   Successfully connected to controller app
   Ping successful
   Initialization complete
   ============================================================
   ```

If you see errors, check the troubleshooting section below.

## Usage

### Starting the System

1. **First, start the controller app:**
   ```bash
   python controller_app/app.py
   ```
   Wait for "IPC listening on 127.0.0.1:5555"

2. **Then start FL Studio** (or reload the script if FL is already running)

3. **Check connection** in FL Studio's Script Output window

### Script Functions

The script automatically handles:

- **Channel enumeration**: Lists all channels with their names
- **Plugin detection**: Identifies plugins on selected channels
- **Parameter control**: Gets/sets plugin parameter values (0-1 normalized)
- **Transport control**: Play, stop, record commands
- **Mixer control**: Volume and pan control for mixer tracks
- **Pattern selection**: Jump to different patterns

All communication happens via ZeroMQ messages. The controller app sends commands, and the script responds with state information.

## Troubleshooting

### "ZeroMQ not available" Warning

**Problem**: PyZMQ is not installed in FL Studio's Python environment.

**Solution**:
1. Verify PyZMQ installation:
   ```bash
   "C:\Program Files\Image-Line\FL Studio 21\Python\python.exe" -c "import zmq; print(zmq.__version__)"
   ```
2. If it fails, reinstall PyZMQ (see Installation Step 1)

### Script Not Listed in MIDI Settings

**Problem**: FL Studio doesn't see the script.

**Solution**:
1. Verify file paths and structure
2. Ensure `device_Definition.py` is present in the controller folder
3. Restart FL Studio
4. Check that the folder name matches the script name

### "Failed to connect" or Connection Timeout

**Problem**: Can't connect to controller app on port 5555.

**Solution**:
1. Ensure controller app is running first
2. Check firewall settings (allow localhost:5555)
3. Verify no other application is using port 5555:
   ```bash
   netstat -ano | findstr :5555
   ```
4. Try restarting both FL Studio and the controller app

### Script Errors in Script Output

**Problem**: Python errors appear in the Script Output window.

**Solution**:
1. Check the error message carefully
2. Verify all imports are available
3. Ensure the `shared` folder is accessible from the controller script path
4. Check Python version compatibility (3.11+ recommended)

### Parameters Not Changing

**Problem**: Setting parameters via the app doesn't affect FL Studio.

**Solution**:
1. Ensure the correct channel/plugin is selected
2. Check that the plugin is valid (not all plugins expose all parameters)
3. Verify parameter indices match (check Script Output for logs)
4. Some plugins require focus to accept parameter changes
5. Try enabling parameter smoothing in the controller app settings

### High CPU Usage

**Problem**: FL Studio becomes slow when script is active.

**Solution**:
1. The script is designed to be lightweight with minimal OnIdle processing
2. Check if the controller app is sending too many messages
3. Reduce parameter update rate in the controller app
4. Disable parameter smoothing if not needed

## Mock Mode (Testing Without FL Studio)

The script includes a mock mode that activates when FL Studio APIs are not available. This is useful for:

- Testing the script logic outside FL Studio
- Running unit tests
- Development on non-Windows systems

In mock mode:
- All FL Studio API calls are simulated
- Mock data is returned (empty channels, default values)
- IPC communication still works (for testing the client)

## Architecture Notes

### Message Flow

1. Controller app sends JSON message via ZeroMQ REQ socket
2. FL Studio script receives message (when processing MIDI or on idle)
3. Script executes the requested action (set parameter, etc.)
4. Script sends JSON response back via ZeroMQ REP socket
5. Controller app receives response and updates UI

### Threading

- The IPC client runs non-blocking to avoid freezing FL Studio
- Connection attempts use exponential backoff (1s → 2s → 4s → 30s max)
- Timeouts are set to 1 second to prevent hanging

### Parameter Smoothing

The script includes an Exponential Moving Average (EMA) smoother to avoid zipper noise when changing parameters rapidly. This is enabled by default with alpha=0.3 (30% new value, 70% old value).

To disable smoothing, call:
```python
set_plugin_parameter(channel, param, value, smooth=False)
```

### Value Scaling

All parameter values are normalized to 0-1 range for consistency across different plugins and external APIs. The script handles clamping automatically.

## Advanced Configuration

### Custom Port

To use a different port, edit `ipc_client.py`:
```python
_ipc_client = IPCClient(host="127.0.0.1", port=5556, timeout_ms=1000)
```

### Adjust Smoothing

To change smoothing behavior, edit `main.py`:
```python
_smoother = ExponentialMovingAverage(alpha=0.5)  # More responsive
_smoother = ExponentialMovingAverage(alpha=0.1)  # Smoother
```

### Reconnection Settings

In `ipc_client.py`, adjust backoff parameters:
```python
self.initial_backoff = 1.0   # Initial retry delay (seconds)
self.max_backoff = 30.0      # Maximum retry delay (seconds)
self.backoff_multiplier = 2.0 # Backoff growth factor
self.max_retries = 3         # Retries per request
```

## Known Limitations

1. **Plugin Slot Detection**: Currently only checks first 10 plugin slots per channel
2. **Parameter Names**: Some plugins don't expose parameter names properly (will show as "Parameter X")
3. **Automation**: Script sets values directly, not via automation clips
4. **Multi-instance**: Only one instance of the script can run at a time
5. **FL 9 Support**: This script requires FL Studio 21+; FL 9 is not supported

## Support

For issues, feature requests, or contributions:
- GitHub Issues: https://github.com/Saiyan9001/fl-ai-producer/issues
- Check the main README.md for general troubleshooting
- Review controller_app logs for detailed error messages

## License

See LICENSE file in the repository root.
