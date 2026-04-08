# Deep Agents Implementation Guide

This guide documents the complete Deep Agents SDK integration for MCP Jose, providing a powerful, production-ready agent framework with streaming, persistence, memory, skills, and human-in-the-loop capabilities.

## Overview

The Deep Agents implementation provides:

- **Real-time Streaming**: Watch agent execution in real-time with tool calls, results, and thinking steps
- **Persistent Memory**: Maintain conversation history across sessions with automatic checkpointing
- **Skills Integration**: Load domain-specific knowledge and workflows
- **Human-in-the-Loop**: Require manual approval for sensitive operations
- **Interactive Sessions**: Chat-style interface with persistent thread management
- **Task Planning**: Decompose complex requests into manageable steps
- **Structured Output**: Type-safe responses with Pydantic validation

## Quick Start

### Basic Usage

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent

# Create agent (automatically initializes Deep Agents SDK)
agent = MCPJoseLangChainDeepAgent(
    model="openai:gpt-5.4",
    enable_streaming=True,
    enable_memory=True,
)

# Single turn
result = agent.invoke("Explain quantum computing", thread_id="conv_001")
print(result["output"])

# Or use the CLI
# python -m langchain_deep_agent "Explain quantum computing" --stream --memory
```

### Interactive Session

```python
from langchain_deep_agent import InteractiveStreamingSession

agent = MCPJoseLangChainDeepAgent(enable_streaming=True)
session = InteractiveStreamingSession(agent)
session.interactive_loop()  # Chat-style REPL
```

### Command Line

```bash
# Simple query
python -m langchain_deep_agent "What is LangGraph?"

# With streaming and persistent memory
python -m langchain_deep_agent "Complex research task" --stream --memory

# Interactive mode
python -m langchain_deep_agent --interactive

# Generate a task plan
python -m langchain_deep_agent "Build a web app" --plan --plan-depth 3

# List available tools
python -m langchain_deep_agent --list-tools

# List discovered skills
python -m langchain_deep_agent --list-skills

# Show conversation history
python -m langchain_deep_agent --show-history --thread-id my_conversation
```

## Core Capabilities

### 1. Streaming Execution

Real-time observation of agent operation:

```python
from langchain_deep_agent import StreamingRunner

agent = MCPJoseLangChainDeepAgent(enable_streaming=True)
runner = StreamingRunner(agent)

# Run with streaming output
result = runner.run(
    user_input="Research topic for me",
    show_intermediate=True,  # Show thinking steps
    show_tool_calls=True,    # Show tool calls and results
)
```

Output events include:
- Tool calls with arguments
- Tool execution results
- Agent thinking/reasoning
- Intermediate steps
- Final response

### 2. Persistent Memory

Maintain conversation state across sessions:

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent

# Same thread_id maintains context
agent = MCPJoseLangChainDeepAgent(
    enable_memory=True,
    thread_id="my_project_001"
)

# First turn
result1 = agent.invoke("Remember: Project uses FastAPI")

# Later session - same thread
result2 = agent.invoke("What tech stack did we discuss?")
# Agent remembers!

# Retrieve history
history = agent.get_thread_history(thread_id="my_project_001")
```

### 3. Task Planning

Decompose complex requests into actionable steps:

```python
plan = agent.plan(
    "Build a full-stack e-commerce platform",
    depth=3  # 1=simple, 2=moderate, 3=detailed
)

print(plan["plan"])
# Returns: main objective, atomic tasks, dependencies,
#          complexity, required tools, risks, success criteria
```

Plan structure:
- Main objective
- Atomic tasks (numbered, independent when possible)
- Task dependencies
- Complexity estimates
- Required tools/skills
- Potential risks
- Success criteria

### 4. Skills Integration

Leverage domain-specific knowledge:

```python
from langchain_deep_agent import SkillsManager

agent = MCPJoseLangChainDeepAgent()
skills_mgr = SkillsManager(repo_root=Path("."))

# Discover skills
skills = skills_mgr.discover_skills()
# Returns: [
#   {"skill_id": "web-artifacts-builder", "description": "..."},
#   {"skill_id": "figma-implement-design", "description": "..."},
#   ...
# ]

# Skills are automatically injected into agent context
```

Skills provide:
- Specialized workflows
- Domain-specific instructions
- Reference materials and templates
- Best practices and patterns

### 5. Human-in-the-Loop

Require manual approval for sensitive operations:

```python
from langchain_deep_agent import HumanInTheLoopConfig

hitl = HumanInTheLoopConfig()

# Standard dangerous tools
hitl.configure_dangerous_tools()
# Configures approval for:
# - delete_file
# - send_email
# - process_payment
# - execute_command
# - etc.

# Or customize
hitl.require_approval("my_tool", allowed_decisions=["approve", "reject"])

agent = MCPJoseLangChainDeepAgent(interrupt_on_tools=hitl.get_interrupt_config())
```

Workflow:
1. Agent selects tool that requires approval
2. User sees operation details
3. User decides: approve / reject / edit / skip
4. If edit, agent modifies parameters before execution

Tracking approvals:

```python
from langchain_deep_agent import OperationApprovalTracker

tracker = OperationApprovalTracker()
tracker.record_decision("delete_file", decision="approve")

# Get statistics
stats = tracker.get_approval_stats()
# Returns: {
#   "total_decisions": 42,
#   "approved": 35,
#   "rejected": 5,
#   "edited": 2,
#   "approval_rate": 0.83,
#   "by_tool": {...}
# }
```

### 6. Memory Management

```python
from langchain_deep_agent import MemoryManager

mem_mgr = MemoryManager(backend_type="memory")

# Load context files
agents_md = mem_mgr.load_agents_md(Path("AGENTS.md"))
memory_md = mem_mgr.load_memory_md(Path("MEMORY.md"))

# Prepare for Deep Agents
files = mem_mgr.prepare_memory_files(
    agents_md_content=agents_md,
    memory_md_content=memory_md,
)
```

### 7. Middleware Configuration

```python
from langchain_deep_agent import MiddlewareConfig

middleware = MiddlewareConfig()

# Add logging
middleware.add_logging_middleware(verbose=True)

# Add automatic retries with backoff
middleware.add_retry_middleware(max_retries=3, backoff_factor=2.0)

# Add rate limiting
middleware.add_rate_limiter_middleware(requests_per_minute=60)

config = middleware.get_middleware_config()
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
