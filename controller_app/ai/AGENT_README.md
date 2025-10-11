# DAW Agent - AI-Powered FL Studio Control

The DAW Agent provides an intelligent interface between natural language queries and FL Studio, allowing users to control their DAW through conversational AI.

## Features

- **Tool-Based Execution**: LLM proposes tool calls based on user queries
- **Preview Mode**: See planned actions before execution (dry-run)
- **Safety Checks**: Validates parameters, prevents destructive actions
- **Flexible Execution**: Apply all actions or selectively choose which to execute
- **Error Handling**: Graceful error reporting with detailed messages

## Architecture

```
User Query → LLM Provider → Tool Calls → Agent Validation → IPC Client → FL Studio
                ↓                            ↓
            Preview Plan              Execution Results
```

## Usage

### Basic Usage

```python
from controller_app.ai import run_agent
from controller_app.ai.providers import OpenAIProvider
from controller_app.ai.templates.tool_schemas import get_tool_schemas
from controller_app.ipc import IPCClient

# Setup
provider = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
tools = get_tool_schemas()
ipc_client = IPCClient()
ipc_client.connect()

# Preview plan
plan = run_agent(
    query="Set the cutoff on the first synth to 0.7",
    provider=provider,
    tools=tools,
    dry_run=True,
)

# Review actions
for action in plan.actions:
    print(f"{action.description} (checked: {action.checked})")

# Execute plan
plan = run_agent(
    query="Set the cutoff on the first synth to 0.7",
    provider=provider,
    tools=tools,
    ipc_client=ipc_client,
    dry_run=False,
)

# Check results
for action in plan.actions:
    if action.error:
        print(f"Error: {action.error}")
    else:
        print(f"Success: {action.result}")
```

### With Ollama

```python
from controller_app.ai.providers import OllamaProvider

provider = OllamaProvider(
    host="http://127.0.0.1:11434",
    model="llama3.1",
)
```

## Available Tools

- **list_state**: Get current FL Studio state
- **get_params**: Get plugin parameters
- **set_param**: Set a plugin parameter (0.0-1.0)
- **set_note_batch**: Add MIDI notes to a channel
- **transport**: Control playback (play, stop, record, etc.)
- **mixer**: Control mixer (volume, pan)
- **channel**: Select a channel

## Safety Features

### Parameter Validation

- **set_param**: Values clamped to 0.0-1.0 range
- **set_note_batch**: MIDI notes validated (pitch: 0-127, velocity: 1-127)
- **Parameter indices**: Must be non-negative integers
- **Transport commands**: Validated against allowed list

### Destructive Action Prevention

The agent blocks potentially destructive actions:
- Resetting all parameters
- Clearing all notes
- Ambiguous "delete all" operations

### Step Budget

Maximum number of tool calls per query is configurable (default: 8).

## Error Handling

```python
from controller_app.ai import AgentError

try:
    plan = run_agent(...)
except AgentError as e:
    print(f"Agent error: {e}")
```

Common errors:
- `Unknown tool`: Tool name not in schema
- `Invalid arguments`: Argument validation failed
- `Too many tool calls`: Exceeded max_steps
- `Destructive action blocked`: Safety check failed

## API Reference

### run_agent()

```python
def run_agent(
    query: str,
    provider: BaseProvider,
    tools: Dict[str, Dict[str, Any]],
    ipc_client: Optional[IPCClient] = None,
    max_steps: int = 8,
    dry_run: bool = True,
    system_prompt: Optional[str] = None,
) -> AgentPlan
```

**Arguments:**
- `query`: User's natural language query
- `provider`: AI provider instance (OpenAI, Ollama, etc.)
- `tools`: Tool schemas from `get_tool_schemas()`
- `ipc_client`: IPC client (required if `dry_run=False`)
- `max_steps`: Maximum number of tool calls allowed
- `dry_run`: If True, only preview actions without executing
- `system_prompt`: Optional custom system prompt

**Returns:** `AgentPlan` object with actions and results

### AgentPlan

```python
@dataclass
class AgentPlan:
    actions: List[ToolCallAction]
    reasoning: str
    raw_response: ChatResponse
```

### ToolCallAction

```python
@dataclass
class ToolCallAction:
    tool_name: str
    arguments: Dict[str, Any]
    description: str
    checked: bool = True
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

## UI Integration

The AI Assistant tab in `main_window.py` provides:
- Provider configuration (OpenAI/Ollama/Auto)
- Model and API key input
- Chat interface for queries
- Action plan preview with checkboxes
- Execution logs and error reporting
- Cancel functionality for long-running operations

## Testing

Run the test suite:

```bash
pytest controller_app/tests/test_agent.py -v
```

Tests cover:
- Tool call description generation
- Argument validation
- Destructive action detection
- Dry-run mode
- Execution with IPC client
- Error handling
- Multi-step plans

## Example Queries

- "Set the cutoff on the first synth to 0.7"
- "Add a C major chord to channel 0"
- "Start playback"
- "Set mixer track 1 volume to 0.8"
- "Get the current state of FL Studio"

## Limitations

- Tool calls are executed sequentially (no parallelization)
- Maximum 8 tool calls per query (configurable)
- No conversation history/context across queries (future feature)
- No automatic state verification (user must verify results)

## Future Enhancements

- [ ] Conversation history for multi-turn interactions
- [ ] Automatic state verification after actions
- [ ] Undo/redo functionality
- [ ] Batch execution optimization
- [ ] Enhanced error recovery
- [ ] Tool call parallelization where safe
