# FL-AI-Producer Test Suite

This directory contains comprehensive tests for the FL-AI-Producer project, covering both the controller app and FL Studio integration scripts.

## Test Files

### `test_ipc_roundtrip.py`
Tests the IPC communication layer between the controller app and FL Studio script.

**Tests:**
- Client creation and connection
- Ping/pong roundtrip
- State retrieval
- Parameter setting (with clamping)
- Transport commands
- Mixer control (volume, pan)
- Channel selection
- Reconnection and error handling
- Mock mode functionality

**Fixtures:**
- `mock_server`: A mock ZeroMQ REP server simulating the controller app
- `ipc_client`: An IPC client connected to the mock server

### `test_fl_controller.py`
Tests the FL Studio controller script functions in mock mode (without FL Studio API).

**Tests:**
- FL entry points (OnInit, OnDeInit, OnIdle, OnMidiIn)
- Channel enumeration
- Plugin enumeration
- Parameter getting/setting
- Parameter clamping and smoothing
- Mixer track enumeration
- Transport command handling
- Mixer command handling
- Channel command handling
- Pattern selection
- Mock mode detection

### `test_shared_utils.py`
Tests the shared utility functions used by both the controller app and FL script.

**Test Classes:**

#### `TestValueScaler`
- Value normalization (0-1)
- Value denormalization
- Clamping
- Roundtrip conversion

#### `TestExponentialMovingAverage`
- Initialization and configuration
- Smoothing behavior
- Multiple key tracking
- Force updates
- Reset functionality

#### `TestConversionFunctions`
- dB ↔ linear conversion
- Linear interpolation
- Discrete value snapping
- Parameter formatting

### `test_integration.py`
End-to-end integration tests demonstrating complete workflows.

**Tests:**
- Full integration workflow (all components working together)
- Parameter smoothing in realistic scenarios
- Error handling and edge cases

## Running Tests

### Run All Tests
```bash
python -m pytest controller_app/tests/ -v
```

### Run Specific Test File
```bash
python -m pytest controller_app/tests/test_ipc_roundtrip.py -v
```

### Run Specific Test
```bash
python -m pytest controller_app/tests/test_integration.py::test_full_integration_workflow -v
```

### Run with Output
```bash
python -m pytest controller_app/tests/ -v -s
```

### Run with Coverage (if coverage installed)
```bash
python -m pytest controller_app/tests/ --cov=fl_scripts --cov=controller_app
```

## Dependencies

- `pytest` - Test framework
- `pyzmq` - ZeroMQ Python bindings for IPC tests

Install with:
```bash
pip install pytest pyzmq
```

## Mock Mode

All tests run in **mock mode** by default, which means:
- FL Studio API is simulated with mock objects
- Tests can run on any platform (Windows/Linux/Mac)
- No FL Studio installation required for testing

This allows for:
- CI/CD integration
- Development on non-Windows systems
- Fast test execution
- Reliable test results

## Test Coverage

Current test coverage:
- **56 tests total**
- All core functionality covered
- IPC communication: ✅
- FL controller functions: ✅
- Shared utilities: ✅
- Integration scenarios: ✅

## Continuous Integration

These tests are designed to run in CI environments. They:
- Don't require FL Studio installation
- Run completely in mock mode
- Complete in ~30 seconds
- Provide comprehensive coverage

## Adding New Tests

When adding new functionality:

1. **Add unit tests** to the appropriate test file
2. **Use mock mode** for FL API calls
3. **Test edge cases** (invalid inputs, errors)
4. **Test the happy path** (normal operation)
5. **Add integration tests** if the feature affects multiple components

Example test structure:
```python
def test_new_feature():
    """Test description."""
    # Setup
    # ... initialize components
    
    # Execute
    result = some_function()
    
    # Assert
    assert result is not None
    assert result.property == expected_value
    
    # Cleanup (if needed)
```

## Troubleshooting

### "ZeroMQ not available" warnings
- Install pyzmq: `pip install pyzmq`
- Tests will fall back to mock mode if ZeroMQ is unavailable

### Import errors
- Ensure you're running tests from the repository root
- Check that `fl_scripts` is in the Python path

### Timeout errors in IPC tests
- The mock server uses port 5556 (not 5555) to avoid conflicts
- Check that no other process is using port 5556

## Future Improvements

Potential enhancements to the test suite:
- Add performance benchmarks
- Test with real FL Studio API (requires Windows + FL Studio)
- Add stress tests (many simultaneous connections)
- Test with different FL Studio versions
- Add UI tests (if GUI is implemented)
