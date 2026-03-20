# LangChain Agent

This folder contains a LangChain tool-calling agent wired to MCP Jose.

## What It Connects

- MCP Jose tools (`search`, `navigate_to_url`, `x_search`, vision, OCR, transcription, image generation, WhatsApp)
- Local filesystem tools from `tools/filesystem.py`
- `AGENTS.md` guidance via `read_agents_md`
- All discovered project `SKILL.md` files via `list_skills` and `read_skill`

## Run

```bash
python -m langchain_agent.main --help

# One-shot prompt
python -m langchain_agent.main "Summarize latest MCP releases and save notes to userapp/notes.txt"

# WhatsApp-only mode
python -m langchain_agent.main --whatsapp

# Inspect capabilities
python -m langchain_agent.main --list-tools
python -m langchain_agent.main --list-skills
python -m langchain_agent.main --show-context
```

## Configuration

The agent loads `auth/.env` automatically (same as the rest of the project).
Set `OPENAI_API_KEY` and any provider-specific credentials required by tools you call.
