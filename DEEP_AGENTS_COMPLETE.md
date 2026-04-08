# Deep Agents Implementation - Updated Documentation

## Summary

The `langchain_deep_agent` package has evolved from a broad Deep Agents feature set into a **parity-focused DeepAgents-backed wrapper** that preserves the same surface behavior as `langchain_agent` while using Deep Agents internally when the dependency is available.

This document reflects the current implementation state and replaces older claims about streaming, HITL, planning, and extra CLI flags that are not part of the current parity target.

---

## What Changed

### Current implementation status

- `langchain_deep_agent/agent.py` now subclasses `MCPJoseLangChainAgent`
- It builds a Deep Agents runtime via `create_deep_agent(tools=self.tools, system_prompt=self.system_prompt)` when the dependency is installed
- If Deep Agents is unavailable, it falls back to the existing agent implementation
- The wrapper preserves access to shared tools and skills through the existing LangChain agent runtime
- The CLI in `langchain_deep_agent/main.py` now mirrors `langchain_agent/main.py` behavior for interactive flow and voice dispatch
- Tests were added/updated to verify CLI parity, voice mode, prompt rendering, and interactive rejection behavior

### Important dependency note

`requirements.txt` currently does **not** list `deepagents`, so the Deep Agents runtime path still requires the package to be installed separately.

---

## Documented parity goals

The deep agent should:

- match the classic agent’s CLI semantics at the surface
- support interactive and voice behavior the same way
- expose the same user-facing entry points where applicable
- internally use Deep Agents when available
- remain backward compatible with the existing agent workflow

---

## Relevant files

- `langchain_deep_agent/agent.py`
- `langchain_deep_agent/main.py`
- `langchain_deep_agent/deepagents_config.py`
- `tests/test_langchain_deep_agent.py`
- `DEEP_AGENTS_COMPLETE.md`
- `langchain_deep_agent/DEEP_AGENTS_GUIDE.md`
- `langchain_deep_agent/IMPLEMENTATION_SUMMARY.md`
- `langchain_deep_agent/QUICKSTART.md`

---

## Suggested next steps

1. Add `deepagents` to `requirements.txt` if the runtime should be available by default
2. Keep the documentation aligned with the parity-based implementation
3. Expand tests if more CLI options or runtime behaviors are added later
4. Verify any future Deep Agents enhancements do not break `langchain_agent` parity

---

## Legacy content note

Older documentation in this repo described a much larger Deep Agents feature set, including:

- streaming execution
- persistent memory via thread management
- planning flags
- human-in-the-loop workflows
- expanded CLI options like `--stream`, `--memory`, `--plan`, `--hitl`, and `--show-history`

Those claims should be treated as historical or aspirational unless they are reintroduced in the codebase.
