# Deep Agents Quick Start

Get up and running with Deep Agents in 5 minutes.

## Installation

The required packages are already in `requirements.txt`:
```bash
pip install -r requirements.txt
```

## 1. Basic Usage

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent

# Create agent
agent = MCPJoseLangChainDeepAgent()

# Ask a question
result = agent.invoke("What is LangGraph?")
print(result["output"])
```

## 2. With Streaming

See agent execution in real-time:

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent, StreamingRunner

agent = MCPJoseLangChainDeepAgent(enable_streaming=True)
runner = StreamingRunner(agent)

# Watch in real-time
result = runner.run("Research quantum computing")
```

## 3. With Persistent Memory

Maintain conversation across turns:

```python
agent = MCPJoseLangChainDeepAgent(
    enable_memory=True,
    thread_id="my_conversation"
)

# First turn
agent.invoke("Remember: I use Python and FastAPI")

# Later (same session or after restart)
result = agent.invoke("What tech stack am I using?")
# Agent remembers!
```

## 4. Generate Task Plans

Break down complex tasks:

```python
plan = agent.plan(
    "Build a full-stack e-commerce site",
    depth=3  # 1=simple, 2=moderate, 3=detailed
)

print(plan["plan"])
```

## 5. Interactive Chat

Chat-style interface:

```python
from langchain_deep_agent import InteractiveStreamingSession

agent = MCPJoseLangChainDeepAgent(enable_streaming=True)
session = InteractiveStreamingSession(agent)

# Start interactive conversation
session.interactive_loop()
# Type queries, press Enter
# Commands: exit, history, clear
```

## Command Line Usage

### Simple query
```bash
python -m langchain_deep_agent "What is LangChain?"
```

### With streaming
```bash
python -m langchain_deep_agent "Task" --stream
```

### Interactive mode
```bash
python -m langchain_deep_agent --interactive
```

### Generate plan
```bash
python -m langchain_deep_agent "Build webapp" --plan --plan-depth 3
```

### List available tools
```bash
python -m langchain_deep_agent --list-tools
```

### List available skills
```bash
python -m langchain_deep_agent --list-skills
```

### With persistent memory
```bash
python -m langchain_deep_agent "Your task" --memory --thread-id my_session
```

## Key Features

| Feature | Enable | Use Case |
|---------|--------|----------|
| **Streaming** | `enable_streaming=True` | Watch agent in real-time |
| **Memory** | `enable_memory=True` | Persistent conversations |
| **Planning** | `agent.plan()` | Break down complex tasks |
| **Skills** | Auto-loaded | Domain knowledge injection |
| **HITL** | Separate config | Approve sensitive ops |

## Configuration Options

```python
agent = MCPJoseLangChainDeepAgent(
    model="openai:gpt-5.4",       # Model to use
    temperature=0.0,              # Deterministic
    enable_streaming=True,        # Real-time output
    enable_memory=True,           # Persistent state
    thread_id="session_001",      # Conversation ID
    verbose=True,                 # Debug output
)
```

## Common Tasks

### Task 1: Research something

```python
agent = MCPJoseLangChainDeepAgent(enable_streaming=True)

result = agent.invoke("Research the latest AI trends in 2025")
```

### Task 2: Plan a project

```python
plan = agent.plan(
    "Implement a recommendation system",
    depth=3
)
print(plan["plan"])
```

### Task 3: Chat session with memory

```python
agent = MCPJoseLangChainDeepAgent(enable_memory=True)
session = InteractiveStreamingSession(agent)
session.interactive_loop()  # Chat naturally
```

### Task 4: Code review with planning

```python
plan = agent.plan("Review and refactor this codebase", depth=2)
# Gets step-by-step review plan
```

## Troubleshooting

**Q: Is streaming not showing?**
A: Make sure `enable_streaming=True` and import `StreamingRunner`

**Q: Memory not persisting?**
A: Use `enable_memory=True` and same `thread_id` across calls

**Q: Which model should I use?**
A: Start with `gpt-5.4-mini` (faster, cheaper), upgrade to `gpt-5.4` for better results

**Q: How do I see conversations?**
A: Use `agent.get_thread_history(thread_id)` or CLI flag `--show-history`

## Next Steps

1. Read the [full guide](./DEEP_AGENTS_GUIDE.md)
2. Explore [examples](./DEEP_AGENTS_GUIDE.md#examples)
3. Check [API reference](./DEEP_AGENTS_GUIDE.md#api-reference)
4. Review [configuration options](./DEEP_AGENTS_GUIDE.md#configuration)

## Learn More

- [LangChain Docs](https://docs.langchain.com/)
- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
