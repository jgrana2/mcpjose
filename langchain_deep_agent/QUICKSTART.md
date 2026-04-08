# Deep Agents Quick Start

This quick start reflects the current documented behavior of `langchain_deep_agent`.
The package is treated as a compatibility wrapper around `langchain_agent`, with optional Deep Agents
support used internally when available.

## Installation

Install the project dependencies as usual:

```bash
pip install -r requirements.txt
```

Note: `deepagents` is not currently listed in `requirements.txt`, so Deep Agents support is optional
and depends on whether that dependency is installed in your environment.

## 1. Basic Usage

```python
from langchain_deep_agent import MCPJoseLangChainDeepAgent

agent = MCPJoseLangChainDeepAgent()
result = agent.invoke("What is LangGraph?")
print(result["output"])
```

## 2. Optional Deep Agents Behavior

If Deep Agents are available in the environment, the wrapper may use them internally while preserving
the same public interface documented for `langchain_agent` parity.

## 3. CLI Usage

Use the package through the same CLI patterns documented for the agent wrapper. Keep examples aligned
with the current implemented flags and behavior.

Example:

```bash
python -m langchain_deep_agent "What is LangChain?"
```

## 4. Documentation Notes

The following capabilities should only be documented if they are verified in the current codebase:

- streaming
- persistent memory
- planning helpers
- human-in-the-loop flows
- extra CLI flags

If those features exist in a specific implementation branch, document them there with explicit runtime
requirements and examples.
