# Deep Agents Implementation Guide

This guide reflects the current `langchain_deep_agent` implementation in MCP Jose. The package is now documented as a **parity-focused wrapper** around the existing LangChain agent surface, with Deep Agents used internally when available.

## Overview

Current behavior emphasizes compatibility over expanded feature claims:

- **LangChain parity**: the deep agent preserves the same user-facing workflow as `langchain_agent`
- **Deep Agents backend when available**: the runtime can use Deep Agents internally if the dependency is installed
- **Fallback behavior**: if Deep Agents is unavailable, the package falls back to the existing agent implementation
- **Shared tools and skills**: the wrapper still exposes the same project tools, prompts, and skill discovery path
- **CLI alignment**: the deep agent CLI mirrors the classic agent CLI behavior at the surface

## What is and isn’t supported today

### Supported

- Same high-level agent entry points as the classic agent
- Interactive and voice behavior aligned with `langchain_agent`
- Tool and skill reuse from the existing agent stack
- Deep Agents runtime path when the package is installed

### Not currently documented as active guarantees

The following items appeared in older docs, but should be treated as historical or aspirational unless reintroduced in code:

- streaming execution APIs
- persistent memory/thread management claims
- planning-specific CLI flags such as `--plan`
- human-in-the-loop workflows as a guaranteed feature set
- extra runtime flags like `--stream`, `--memory`, `--hitl`, or `--show-history`
- structured output guarantees tied to Deep Agents specifically

## Quick Start

### Basic Usage

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent

agent = MCPJoseLangChainDeepAgent()
result = agent.invoke("Explain quantum computing")
print(result)
```

### Command Line

```bash
# Simple query
python -m langchain_deep_agent "What is LangGraph?"

# Interactive mode
python -m langchain_deep_agent --interactive

# Voice mode, if supported by the shared agent flow
python -m langchain_deep_agent --voice
```

## Implementation Notes

### Agent runtime

- `langchain_deep_agent/agent.py` subclasses `MCPJoseLangChainAgent`
- It attempts to build a Deep Agents runtime with `create_deep_agent(tools=self.tools, system_prompt=self.system_prompt)`
- If the dependency is missing, the existing agent implementation is used instead

### CLI behavior

- `langchain_deep_agent/main.py` now mirrors the classic `langchain_agent/main.py` flow
- Tests cover CLI parity, voice dispatch, prompt rendering, and interactive rejection behavior

### Dependency note

`deepagents` is not currently listed in `requirements.txt`, so the Deep Agents backend path still requires separate installation.

## Relevant Files

- `langchain_deep_agent/agent.py`
- `langchain_deep_agent/main.py`
- `langchain_deep_agent/deepagents_config.py`
- `tests/test_langchain_deep_agent.py`
- `DEEP_AGENTS_COMPLETE.md`
- `langchain_deep_agent/IMPLEMENTATION_SUMMARY.md`
- `langchain_deep_agent/QUICKSTART.md`

## Keeping Docs Consistent

When updating this area, make sure the docs all tell the same story:

1. `DEEP_AGENTS_COMPLETE.md` for repo-wide implementation status
2. `langchain_deep_agent/DEEP_AGENTS_GUIDE.md` for package-level usage notes
3. `IMPLEMENTATION_SUMMARY.md` and `QUICKSTART.md` for user-facing details

If new Deep Agents features are added later, document them only after verifying the code and tests actually support them.
```

## Architecture

```
MCPJoseLangChainDeepAgent (Full-featured Deep Agent)
├── Streaming Support
│   ├── Real-time event streaming
│   ├── Tool call visibility
│   └── Progress tracking
├── Persistence
│   ├── Checkpointing (MemorySaver)
│   ├── Thread management
│   └── History retrieval
├── Memory
│   ├── Persistent stores
│   ├── AGENTS.md context
│   └── MEMORY.md preferences
├── Skills
│   ├── Skill discovery
│   ├── Knowledge injection
│   └── Cost reduction (token usage)
└── Human-in-the-Loop
    ├── Operation approval
    ├── Parameter editing
    └── Decision tracking
```

## API Reference

### MCPJoseLangChainDeepAgent

Main agent class with full Deep Agents SDK integration.

**Constructor**

```python
MCPJoseLangChainDeepAgent(
    repo_root: Optional[Path] = None,
    model: str = "gpt-5.4-mini",                  # LLM model identifier
    temperature: float = 0.0,                     # Sampling temperature
    max_iterations: int = 12,                     # Max agent loop iterations
    verbose: bool = False,                        # Debug logging
    enable_memory: bool = True,                   # Persistent checkpointing
    enable_streaming: bool = True,                # Real-time streaming
    thread_id: Optional[str] = None,              # Thread identifier
    interrupt_on_tools: Optional[dict] = None,    # HITL configuration
)
```

**Methods**

- `invoke(user_input, chat_history, thread_id, config)` → Execute one turn
- `stream(user_input, chat_history, thread_id, config)` → Stream execution
- `plan(user_input, depth)` → Generate task decomposition
- `get_thread_history(thread_id)` → Retrieve conversation history
- `clear_thread(thread_id)` → Clear persisted state

### StreamingRunner

Execute agent with real-time output handling.

```python
StreamingRunner(
    agent: MCPJoseLangChainDeepAgent,
    show_intermediate: bool = True,  # Display thinking steps
    show_tool_calls: bool = True,    # Display tool calls
    show_metadata: bool = False,     # Display timestamps, IDs
)
```

### InteractiveStreamingSession

Chat-style interface with persistent thread.

```python
session = InteractiveStreamingSession(agent)
session.chat("Your message")      # Single turn
session.interactive_loop()        # REPL-style
```

## Configuration

### Environment Variables

```bash
# Model provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...

# Memory store (optional)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...

# Deep Agents specific
DEEPAGENTS_ENABLE_STREAMING=true
DEEPAGENTS_ENABLE_MEMORY=true
```

### Model Selection

Supports any model with tool calling capability:

```python
# OpenAI
agent = MCPJoseLangChainDeepAgent(model="openai:gpt-5.4")

# Anthropic
agent = MCPJoseLangChainDeepAgent(model="anthropic:claude-sonnet-4-6")

# Google
agent = MCPJoseLangChainDeepAgent(model="google:gemini-2.0-flash")

# AWS Bedrock
agent = MCPJoseLangChainDeepAgent(model="bedrock:anthropic.claude-3-5-sonnet")
```

## Examples

### Example 1: Research Task with Streaming

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent, StreamingRunner

agent = MCPJoseLangChainDeepAgent(enable_streaming=True)
runner = StreamingRunner(agent)

result = runner.run(
    "Research the latest advances in quantum computing",
    show_intermediate=True,
)
```

### Example 2: Interactive Knowledge Capture

```python
from langchain_deep_agent import InteractiveStreamingSession

agent = MCPJoseLangChainDeepAgent(
    enable_memory=True,
    thread_id="project_notes"
)

session = InteractiveStreamingSession(agent)
# Have a conversation - all persisted
session.interactive_loop()

# Later: retrieve what was discussed
history = agent.get_thread_history()
```

### Example 3: Sensitive Operation Approval

```python
from langchain_deep_agent import (
    MCPJoseLangChainDeepAgent,
    HumanInTheLoopConfig,
    OperationApprovalTracker,
)

hitl = HumanInTheLoopConfig()
hitl.configure_dangerous_tools()

tracker = OperationApprovalTracker()

agent = MCPJoseLangChainDeepAgent(
    interrupt_on_tools=hitl.get_interrupt_config()
)

# User will be prompted for approval when agent
# tries to delete files, send emails, etc.
result = agent.invoke("Clean up old temp files")

# Review what was approved/rejected
stats = tracker.get_approval_stats()
```

### Example 4: Complex Task Decomposition

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent

agent = MCPJoseLangChainDeepAgent()

# Generate detailed plan
plan = agent.plan(
    "Build and deploy a production search engine",
    depth=3  # Detailed planning
)

print(plan["plan"])
# Outputs structured task breakdown with:
# - Main objective
# - Atomic tasks and dependencies
# - Complexity estimates
# - Required tools and skills
# - Risk assessment
# - Success criteria
```

## Troubleshooting

### Deep Agents import fails

```python
# Check if deepagents is installed
pip install -U deepagents

# Verify import
python -c "from deepagents import create_deep_agent; print('OK')"
```

### Streaming not showing output

```python
# Enable streaming explicitly
agent = MCPJoseLangChainDeepAgent(enable_streaming=True)

from langchain_deep_agent import StreamingRunner
runner = StreamingRunner(agent)
runner.run("Your task")
```

### Memory not persisting

```python
# Check checkpointer is active
agent = MCPJoseLangChainDeepAgent(enable_memory=True, verbose=True)

# Use same thread_id for persistence
result = agent.invoke("Task", thread_id="same_thread_id")

# Verify history exists
history = agent.get_thread_history("same_thread_id")
print(f"Messages in history: {len(history)}")
```

### HITL not interrupting

```python
# Verify tools are configured
hitl_config = HumanInTheLoopConfig()
hitl_config.require_approval("my_tool")

agent = MCPJoseLangChainDeepAgent(
    interrupt_on_tools=hitl_config.get_interrupt_config(),
    verbose=True  # See what's happening
)
```

## Performance Tuning

### Reduce Token Usage

```python
agent = MCPJoseLangChainDeepAgent(
    model="gpt-5.4-mini",  # Smaller model
    temperature=0.0,       # Deterministic
)

# Load skills (auto-disclosed when relevant)
skills_mgr = SkillsManager(repo_root)
skills = skills_mgr.discover_skills()
```

### Faster Responses

```python
agent = MCPJoseLangChainDeepAgent(
    model="gpt-5.4-mini",  # Faster inference
    max_iterations=5,      # Fewer iterations
)
```

### Better Results

```python
agent = MCPJoseLangChainDeepAgent(
    model="gpt-5.4",          # More capable
    temperature=0.2,          # Slight randomness for creativity
    enable_streaming=True,    # Monitor quality in real-time
)
```

## See Also

- [LangChain Documentation](https://docs.langchain.com/)
- [Deep Agents SDK Documentation](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [MCP Jose Project](../README.md)
