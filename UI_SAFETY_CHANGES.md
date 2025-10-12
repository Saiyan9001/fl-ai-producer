# UI Changes - Safety Features

## AI Assistant Tab - New "Safety & Privacy Settings" Section

The AI Assistant tab now includes a new "Safety & Privacy Settings" group box with two checkboxes:

```
┌─────────────────────────────────────────────────────────────────┐
│ Provider Configuration                                          │
│   Provider: [Auto ▼]                                           │
│   Model: [gpt-4o-mini or llama3.1]                            │
│   API Key: [••••••••••••••••••]                               │
│   Ollama Host: [http://127.0.0.1:11434]                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Safety & Privacy Settings                                       │
│                                                                  │
│  ☐ Enable Network Telemetry (opt-in)                           │
│     📊 Local logging is always enabled. Network telemetry       │
│        is opt-in only.                                          │
│                                                                  │
│  ☐ Safe Mode (stricter limits)                                 │
│     🛡️ Reduces max notes/operations and enforces stricter      │
│        rate limits.                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Feature Details

### 1. Network Telemetry Checkbox
- **Label:** "Enable Network Telemetry (opt-in)"
- **Default State:** Unchecked (disabled)
- **Info Text:** "📊 Local logging is always enabled. Network telemetry is opt-in only."
- **Behavior:**
  - When checked: Enables network telemetry (if future network endpoint is configured)
  - When unchecked: Only local logging to `~/.fl-ai-producer/telemetry/`
  - Shows feedback in Results/Logs area

### 2. Safe Mode Checkbox
- **Label:** "Safe Mode (stricter limits)"
- **Default State:** Unchecked (normal mode)
- **Info Text:** "🛡️ Reduces max notes/operations and enforces stricter rate limits."
- **Behavior:**
  - When checked: Reduces limits by 50%
    - Max notes: 128 → 64
    - Max tool executions/min: 60 → 30
    - Max tool executions/query: 16 → 8
  - When unchecked: Normal limits apply
  - Shows feedback in Results/Logs area

## User Feedback Messages

When toggling the checkboxes, users see immediate feedback in the "Results / Logs" area:

**Network Telemetry Enabled:**
```
📊 Network telemetry enabled (opt-in)
```

**Network Telemetry Disabled:**
```
📊 Network telemetry disabled (local-only logging continues)
```

**Safe Mode Enabled:**
```
🛡️ Safe mode enabled (stricter limits active)
```

**Safe Mode Disabled:**
```
🛡️ Safe mode disabled (normal limits active)
```

## Visual Design

### Colors and Styling
- **Info Text:** Gray color (`color: gray; font-size: 10px;`)
- **Emojis:** Used for visual distinction
  - 📊 for telemetry
  - 🛡️ for safe mode
- **Checkboxes:** Standard Qt checkboxes
- **Group Box:** Standard Qt group box with title

### Layout
- **Vertical Layout:** Settings stacked vertically
- **Horizontal Layout:** Each setting has label + info text in horizontal arrangement
- **Stretch:** Adds stretch after info text to prevent unnecessary width expansion

## Implementation Details

### File Modified
- `controller_app/ui/main_window.py`

### New UI Components
```python
# Safety and Privacy Settings
safety_group = QGroupBox("Safety & Privacy Settings")
safety_layout = QVBoxLayout()

# Telemetry opt-in checkbox
self.telemetry_checkbox = QCheckBox("Enable Network Telemetry (opt-in)")
self.telemetry_checkbox.setChecked(False)  # Disabled by default
self.telemetry_checkbox.stateChanged.connect(self._on_telemetry_changed)

# Safe mode checkbox
self.safe_mode_checkbox = QCheckBox("Safe Mode (stricter limits)")
self.safe_mode_checkbox.setChecked(False)  # Disabled by default
self.safe_mode_checkbox.stateChanged.connect(self._on_safe_mode_changed)
```

### Event Handlers
```python
def _on_telemetry_changed(self, state: int):
    """Handle telemetry checkbox change."""
    enabled = state == Qt.CheckState.Checked.value
    telemetry = get_telemetry()
    telemetry.enable_network_telemetry(enabled)
    # Show feedback message

def _on_safe_mode_changed(self, state: int):
    """Handle safe mode checkbox change."""
    enabled = state == Qt.CheckState.Checked.value
    guardrails = get_guardrails()
    guardrails.enable_safe_mode(enabled)
    # Show feedback message
```

## Position in UI Hierarchy

```
Main Window
└── Tabs
    └── AI Assistant
        └── Assistant (sub-tab)
            ├── Provider Configuration [Group Box]
            ├── Safety & Privacy Settings [Group Box] ← NEW!
            ├── Alert Banner
            ├── Template Selector
            ├── Demo Prompt Selector
            ├── Chat/Query [Splitter]
            │   ├── Input Area
            │   ├── Action Plan
            │   └── Results/Logs
            └── Progress Bar
```

## Privacy Indicators

The UI clearly communicates privacy guarantees:

1. **"Local logging is always enabled"** - Users know logging happens
2. **"Network telemetry is opt-in only"** - Users know it's disabled by default
3. **Checkbox is unchecked by default** - Visual confirmation
4. **Immediate feedback** - Users see when telemetry state changes

## Accessibility

- Checkbox labels are descriptive
- Info text provides context
- Emojis add visual distinction (but text is readable without them)
- Standard Qt widgets ensure keyboard navigation works
- State changes are logged to Results area for confirmation

## Future Enhancements

Potential UI improvements:
- [ ] Add "View Telemetry Logs" button
- [ ] Show rate limit status in UI
- [ ] Add "Clear Local Logs" button
- [ ] Display current guardrail limits in info panel
- [ ] Add progress indicator for rate limit cooldown
