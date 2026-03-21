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

# Interactive terminal session
python -m langchain_agent.main --interactive

# Interactive voice input
python -m langchain_agent.main --interactive --voice

# WhatsApp-only mode
python -m langchain_agent.main --whatsapp

# Inspect capabilities
python -m langchain_agent.main --list-tools
python -m langchain_agent.main --list-skills
python -m langchain_agent.main --show-context
```

Interactive mode keeps the conversation history in memory for the current terminal session.
When `--voice` is enabled, it first prompts you to choose a microphone, then press Enter on an empty prompt to record a spoken turn.
The recorder uses an installed external command (`ffmpeg` preferred, `rec` from SoX as fallback).
Responses in terminal sessions are rendered as Markdown when supported by the terminal, with a plain-text fallback otherwise.

## Configuration

The agent loads `auth/.env` automatically (same as the rest of the project).
Set `OPENAI_API_KEY` and any provider-specific credentials required by tools you call.
