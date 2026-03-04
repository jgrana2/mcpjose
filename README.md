# MCP Jose

**MCP Jose** is a unified **MCP (Model Context Protocol) server** that exposes a collection of AI-powered tools (vision, OCR, image generation, transcription, web search, messaging) behind a single server.

## Features

- **Vision**: OpenAI Vision + Gemini Vision
- **OCR**: Google Cloud Vision OCR
- **Image generation**: Gemini
- **Audio transcription**: OpenAI Whisper
- **Web search & navigation**: search + page/PDF extraction
- **WhatsApp messaging**: Meta Cloud API

## Repository layout

- `mcp_server/` – MCP server implementation
- `tools/` – Individual tool modules
- `providers/` – Provider implementations (OpenAI, Gemini, Google, etc.)
- `core/` – Shared utilities/config
- `auth/` – Authentication handling
- `tests/` – Test suite
- `.agents/` / `skills/` – Agent Skills used by coding agents

## Setup

```bash
pip install -r requirements.txt

# or activate the included virtual environment
source env/bin/activate
```

## Run

```bash
# Start the MCP server
python -m mcp_server.server

# CLI help (if available)
python cli.py --help
```

## Testing

```bash
pytest
# or
pytest -v
```

## Linting

```bash
ruff check .
ruff format .
```

## Notes

Credentials/API keys are managed via the project configuration utilities (see `core/` and provider modules). Depending on the tools you use, you may need keys for OpenAI, Google Cloud Vision, Gemini, and/or Meta WhatsApp Cloud API.
