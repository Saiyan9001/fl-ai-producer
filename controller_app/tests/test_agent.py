"""
Tests for DAW Agent

Tests agent loop with mocked provider and IPC client.
"""
import pytest
from unittest.mock import Mock, MagicMock
from controller_app.ai.agent import (
    run_agent,
    AgentPlan,
    AgentError,
    ToolCallAction,
    _describe_tool_call,
    _validate_tool_arguments,
    _is_destructive_action,
)
from controller_app.ai.providers.base import ChatResponse, ToolCall
from controller_app.ai.templates.tool_schemas import get_tool_schemas


class MockProvider:
    """Mock AI provider for testing."""
    
    def __init__(self, tool_calls=None, content="Here's what I'll do:"):
        """
        Initialize mock provider.
        
        Args:
            tool_calls: List of ToolCall objects to return
            content: Text content to return
        """
        self.tool_calls = tool_calls or []
        self.content = content
    
    def chat(self, messages, tools=None, tool_choice=None, stream=False):
        """Mock chat method."""
        return ChatResponse(
            content=self.content,
            tool_calls=self.tool_calls,
            usage={"input_tokens": 100, "output_tokens": 50},
        )


class MockIPCClient:
    """Mock IPC client for testing."""
    
    def __init__(self):
        """Initialize mock IPC client."""
        self.calls = []
    
    def list_state(self):
        """Mock list_state."""
        self.calls.append(("list_state", {}))
        return {"channels": [], "plugins": [], "mixer_tracks": []}
    
    def get_params(self, plugin_ref):
        """Mock get_params."""
        self.calls.append(("get_params", {"plugin_ref": plugin_ref}))
        return {"parameters": []}
    
    def set_param(self, plugin_ref, index, value01):
        """Mock set_param."""
        self.calls.append(("set_param", {
            "plugin_ref": plugin_ref,
            "index": index,
            "value01": value01,
        }))
        return {"success": True}
    
    def set_note_batch(self, channel_ref, notes):
        """Mock set_note_batch."""
        self.calls.append(("set_note_batch", {
            "channel_ref": channel_ref,
            "notes": notes,
        }))
        return {"success": True, "notes_added": len(notes)}
    
    def transport(self, cmd):
        """Mock transport."""
        self.calls.append(("transport", {"cmd": cmd}))
        return {"success": True}
    
    def mixer(self, action, track, value):
        """Mock mixer."""
        self.calls.append(("mixer", {
            "action": action,
            "track": track,
            "value": value,
        }))
        return {"success": True}
    
    def channel(self, select_index):
        """Mock channel."""
        self.calls.append(("channel", {"select_index": select_index}))
        return {"success": True}


def test_describe_tool_call():
    """Test tool call description generation."""
    # Test set_param
    desc = _describe_tool_call("set_param", {
        "plugin_ref": "0:0",
        "index": 5,
        "value01": 0.75,
    })
    assert "0:0" in desc
    assert "5" in desc
    assert "0.75" in desc
    
    # Test set_note_batch
    desc = _describe_tool_call("set_note_batch", {
        "channel_ref": "2",
        "notes": [{"pitch": 60}] * 4,
    })
    assert "4 notes" in desc
    assert "channel 2" in desc
    
    # Test transport
    desc = _describe_tool_call("transport", {"cmd": "play"})
    assert "play" in desc


def test_validate_tool_arguments():
    """Test tool argument validation."""
    # Valid set_param
    error = _validate_tool_arguments("set_param", {
        "plugin_ref": "0:0",
        "index": 5,
        "value01": 0.5,
    })
    assert error is None
    
    # Invalid set_param - value out of range
    error = _validate_tool_arguments("set_param", {
        "plugin_ref": "0:0",
        "index": 5,
        "value01": 1.5,
    })
    assert error is not None
    assert "0.0-1.0" in error
    
    # Invalid set_param - negative index
    error = _validate_tool_arguments("set_param", {
        "plugin_ref": "0:0",
        "index": -1,
        "value01": 0.5,
    })
    assert error is not None
    
    # Valid set_note_batch
    error = _validate_tool_arguments("set_note_batch", {
        "channel_ref": "0",
        "notes": [
            {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 100},
        ],
    })
    assert error is None
    
    # Invalid set_note_batch - missing field
    error = _validate_tool_arguments("set_note_batch", {
        "channel_ref": "0",
        "notes": [
            {"pitch": 60, "start": 0.0},  # Missing duration and velocity
        ],
    })
    assert error is not None
    
    # Invalid set_note_batch - pitch out of range
    error = _validate_tool_arguments("set_note_batch", {
        "channel_ref": "0",
        "notes": [
            {"pitch": 128, "start": 0.0, "duration": 1.0, "velocity": 100},
        ],
    })
    assert error is not None


def test_is_destructive_action():
    """Test destructive action detection."""
    # Not destructive
    is_dest, reason = _is_destructive_action("set_param", {
        "plugin_ref": "0:0",
        "index": 5,
        "value01": 0.5,
    })
    assert not is_dest
    
    # Transport is not considered destructive
    is_dest, reason = _is_destructive_action("transport", {"cmd": "stop"})
    assert not is_dest


def test_agent_dry_run_with_set_param():
    """Test agent dry run with set_param tool call."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="set_param",
                arguments={
                    "plugin_ref": "0:0",
                    "index": 3,
                    "value01": 0.63,
                },
            ),
        ],
        content="Setting the cutoff filter to 0.63",
    )
    
    # Run agent in dry-run mode
    plan = run_agent(
        query="Set the cutoff on the first plugin to 0.63",
        provider=provider,
        tools=tools,
        dry_run=True,
    )
    
    # Verify plan
    assert isinstance(plan, AgentPlan)
    assert len(plan.actions) == 1
    
    action = plan.actions[0]
    assert action.tool_name == "set_param"
    assert action.arguments["plugin_ref"] == "0:0"
    assert action.arguments["index"] == 3
    assert action.arguments["value01"] == 0.63
    assert action.checked is True
    assert action.result is None  # Not executed in dry-run
    assert action.error is None


def test_agent_dry_run_with_multiple_tools():
    """Test agent dry run with multiple tool calls."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="set_param",
                arguments={
                    "plugin_ref": "0:0",
                    "index": 5,
                    "value01": 0.8,
                },
            ),
            ToolCall(
                name="set_note_batch",
                arguments={
                    "channel_ref": "1",
                    "notes": [
                        {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 100},
                        {"pitch": 64, "start": 1.0, "duration": 1.0, "velocity": 100},
                    ],
                },
            ),
        ],
        content="I'll adjust the parameter and add some notes",
    )
    
    # Run agent
    plan = run_agent(
        query="Set param 5 to 0.8 and add two notes to channel 1",
        provider=provider,
        tools=tools,
        dry_run=True,
    )
    
    # Verify plan
    assert len(plan.actions) == 2
    
    # First action
    assert plan.actions[0].tool_name == "set_param"
    assert plan.actions[0].arguments["value01"] == 0.8
    
    # Second action
    assert plan.actions[1].tool_name == "set_note_batch"
    assert len(plan.actions[1].arguments["notes"]) == 2


def test_agent_execute_with_ipc_client():
    """Test agent execution with IPC client."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="set_param",
                arguments={
                    "plugin_ref": "0:0",
                    "index": 2,
                    "value01": 0.5,
                },
            ),
        ],
    )
    ipc_client = MockIPCClient()
    
    # Run agent with execution
    plan = run_agent(
        query="Set parameter 2 to 0.5",
        provider=provider,
        tools=tools,
        ipc_client=ipc_client,
        dry_run=False,
    )
    
    # Verify execution
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.result is not None
    assert action.result["success"] is True
    assert action.error is None
    
    # Verify IPC client was called
    assert len(ipc_client.calls) == 1
    call_name, call_args = ipc_client.calls[0]
    assert call_name == "set_param"
    assert call_args["plugin_ref"] == "0:0"
    assert call_args["index"] == 2
    assert call_args["value01"] == 0.5


def test_agent_execute_with_note_batch():
    """Test agent execution with set_note_batch."""
    # Setup
    tools = get_tool_schemas()
    notes = [
        {"pitch": 60, "start": 0.0, "duration": 0.5, "velocity": 100},
        {"pitch": 64, "start": 0.5, "duration": 0.5, "velocity": 100},
        {"pitch": 67, "start": 1.0, "duration": 0.5, "velocity": 100},
    ]
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="set_note_batch",
                arguments={
                    "channel_ref": "0",
                    "notes": notes,
                },
            ),
        ],
    )
    ipc_client = MockIPCClient()
    
    # Run agent
    plan = run_agent(
        query="Add a C major chord",
        provider=provider,
        tools=tools,
        ipc_client=ipc_client,
        dry_run=False,
    )
    
    # Verify execution
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.result is not None
    assert action.result["notes_added"] == 3
    
    # Verify IPC client was called
    assert len(ipc_client.calls) == 1
    call_name, call_args = ipc_client.calls[0]
    assert call_name == "set_note_batch"
    assert len(call_args["notes"]) == 3


def test_agent_no_tool_calls():
    """Test agent when no tool calls are needed."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[],  # No tool calls
        content="I don't need to make any changes for that.",
    )
    
    # Run agent
    plan = run_agent(
        query="Just tell me what you think",
        provider=provider,
        tools=tools,
        dry_run=True,
    )
    
    # Verify no actions
    assert len(plan.actions) == 0
    assert "don't need" in plan.reasoning


def test_agent_too_many_steps():
    """Test agent with too many tool calls."""
    # Setup
    tools = get_tool_schemas()
    # Create 10 tool calls (more than max_steps)
    tool_calls = [
        ToolCall(
            name="set_param",
            arguments={"plugin_ref": "0:0", "index": i, "value01": 0.5},
        )
        for i in range(10)
    ]
    provider = MockProvider(tool_calls=tool_calls)
    
    # Run agent with max_steps=5
    with pytest.raises(AgentError, match="Too many tool calls"):
        run_agent(
            query="Do many things",
            provider=provider,
            tools=tools,
            max_steps=5,
            dry_run=True,
        )


def test_agent_invalid_tool():
    """Test agent with invalid tool name."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="invalid_tool",
                arguments={},
            ),
        ],
    )
    
    # Run agent
    with pytest.raises(AgentError, match="Unknown tool"):
        run_agent(
            query="Do something",
            provider=provider,
            tools=tools,
            dry_run=True,
        )


def test_agent_invalid_arguments():
    """Test agent with invalid tool arguments."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="set_param",
                arguments={
                    "plugin_ref": "0:0",
                    "index": 5,
                    "value01": 2.0,  # Out of range
                },
            ),
        ],
    )
    
    # Run agent
    with pytest.raises(AgentError, match="Invalid arguments"):
        run_agent(
            query="Set parameter to invalid value",
            provider=provider,
            tools=tools,
            dry_run=True,
        )


def test_agent_requires_ipc_client_for_execution():
    """Test that agent requires IPC client when not in dry-run mode."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="set_param",
                arguments={
                    "plugin_ref": "0:0",
                    "index": 1,
                    "value01": 0.5,
                },
            ),
        ],
    )
    
    # Try to execute without IPC client
    with pytest.raises(AgentError, match="ipc_client is required"):
        run_agent(
            query="Set parameter",
            provider=provider,
            tools=tools,
            ipc_client=None,
            dry_run=False,
        )


def test_agent_unchecked_actions_not_executed():
    """Test that unchecked actions are skipped during execution."""
    # Setup
    tools = get_tool_schemas()
    provider = MockProvider(
        tool_calls=[
            ToolCall(
                name="set_param",
                arguments={
                    "plugin_ref": "0:0",
                    "index": 1,
                    "value01": 0.5,
                },
            ),
            ToolCall(
                name="transport",
                arguments={"cmd": "play"},
            ),
        ],
    )
    ipc_client = MockIPCClient()
    
    # Run agent
    plan = run_agent(
        query="Set param and play",
        provider=provider,
        tools=tools,
        ipc_client=ipc_client,
        dry_run=False,
    )
    
    # Uncheck second action
    plan.actions[1].checked = False
    
    # Re-execute only checked actions
    executed_count = sum(1 for action in plan.actions if action.checked and action.result)
    assert executed_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
