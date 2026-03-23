# MCP Jose

**MCP Jose** is a unified **MCP (Model Context Protocol) server** that exposes a comprehensive collection of AI-powered tools behind a single server. It includes vision, OCR, image generation, transcription, web search, messaging, and subscription/payment utilities.

## Features

### AI & Vision Processing
- **Vision Analysis**: OpenAI Vision + Gemini Vision for image understanding
- **OCR (Optical Character Recognition)**: Google Cloud Vision OCR for text extraction from images and PDFs
- **Image Generation**: Create images from text prompts using Gemini
- **Audio Transcription**: Convert speech to text using OpenAI Whisper
- **LLM Integration**: Text generation with OpenAI models

### Web & Search
- **Web Search**: Search the web using DuckDuckGo or Google
- **Page Navigation**: Extract content from URLs and PDFs
- **X/Twitter Search**: Search for posts on specific topics
- **Content Extraction**: Read and process web pages and documents

### Messaging & Communication
- **WhatsApp Messaging**: Send messages via Meta WhatsApp Cloud API
- **Template Messages**: Support for WhatsApp template messages
- **Rate Limiting**: Built-in rate limiting for API calls

### Payments & Subscriptions
- **Mercado Pago Subscriptions**: Create subscription checkout links and track preapproval status
- **Webhook Processing**: Sync Mercado Pago subscription updates into SQLite
- **Subscription Guarding**: Gate premium access based on subscription status

### Development & Agent Support
- **Agent Skills**: Specialized skills for coding agents (research, docs, design, web development, communication, etc.)
- **LangChain Agent**: Dedicated LangChain tool-calling agent wired to project tools, skills, and `AGENTS.md`
- **CLI Interface**: Command-line tools for direct tool execution
- **Provider Pattern**: Clean abstraction for different AI service providers
- **Configuration Management**: Secure credential handling with singleton pattern

## Architecture

```
/
├── .agents/              # Agent Skills for enhanced capabilities
│   └── skills/           # Domain-specific knowledge modules
├── mcp_server/           # Main MCP server implementation
├── core/                 # Core utilities and interfaces
│   ├── config.py         # Credential management
│   ├── utils.py          # Helper functions
│   └── rate_limit.py     # Rate limiting implementation
├── providers/            # AI provider implementations
├── tools/                # Individual tool modules
│   ├── navigation.py     # Web navigation tools
│   ├── whatsapp.py       # WhatsApp messaging tools
│   ├── payment_gateway.py # Mercado Pago subscription checkout tools
│   ├── payment_webhook.py # Mercado Pago webhook processing
│   └── search.py         # Search tools
├── auth/                 # Authentication handling
├── tests/                # Test suite
├── userapp/              # User application code
├── langchain_agent/      # LangChain agent integration package
└── cli.py                # CLI entry points
```

## Quick Start

### Prerequisites
- Python 3.8+
- API keys for services you plan to use (OpenAI, Google Cloud, etc.)
- Mercado Pago access token and webhook secret if you plan to use subscriptions

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mcpjose

# Install dependencies
pip install -r requirements.txt

# Or activate the included virtual environment
source env/bin/activate
```

### Configuration

Create a `.env` file in the `auth/` directory with your API keys:

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Google Cloud
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_PROJECT_ID=your_project_id

# Search
SEARCH_ENGINE=ddgs  # or 'pse' for Google

# WhatsApp
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id

# Mercado Pago
MERCADOPAGO_ACCESS_TOKEN=your_mercadopago_access_token
MP_PAYER_EMAIL=buyer@example.com
MP_WEBHOOK_SECRET=your_webhook_secret
```

### Running the MCP Server

```bash
# Start the MCP server
python -m mcp_server.server
```

### Using CLI Tools

```bash
# Get help with available CLI commands
python cli.py --help

# List all shared tools exposed by the registry
python cli.py tool list

# Call a tool with JSON arguments
python cli.py tool call call_llm --json '{"prompt": "Your prompt here"}'

# Call a tool with repeated key=value arguments
python cli.py tool call search --arg query="latest AI developments"

# Run OCR via the shared registry
python cli.py tool call google_ocr --arg input_file=document.pdf --arg file_type=pdf

# Search Google Maps places
python cli.py tool call search_places --arg query="coffee shops" --arg max_results=3

# Send WhatsApp messages
python cli.py tool call send_ws_msg --arg destination="+1234567890" --arg message="Hello from MCP Jose!"

# Create a Mercado Pago subscription link
python cli.py tool call mp_create_checkout_link --arg phone_number="+573002612420"

# Simulate a Mercado Pago webhook payload
python cli.py tool call mp_simulate_webhook --json '{"payload":"{\"type\":\"subscription_preapproval\",\"data\":{\"id\":\"sub_123\"}}"}'

# Run the webhook server
python cli.py whatsapp-webhook --port 5000
```

### Using the LangChain Agent

```bash
# List available tool wrappers
python -m langchain_agent.main --list-tools

# List discovered project skills (SKILL.md files)
python -m langchain_agent.main --list-skills

# Run a one-shot prompt
python -m langchain_agent.main "Use available skills and tools to research MCP updates"

# Run over WhatsApp
python -m langchain_agent.main --whatsapp

# Speak to the interactive agent instead of typing
python -m langchain_agent.main --interactive --voice
```

## Available Tools

### MCP Server Tools
The following tools are available when running the MCP server:

| Tool | Description | Parameters |
|------|-------------|------------|
| `search` | Search the web | `query` |
| `navigate_to_url` | Extract content from URLs | `url` |
| `x_search` | Search X/Twitter | `topic` |
| `call_llm` | Generate text with OpenAI | `prompt` |
| `openai_vision_tool` | Process images with OpenAI Vision | `image_path`, `prompt` |
| `gemini_vision_tool` | Process images with Gemini Vision | `image_path`, `prompt` |
| `transcribe_audio` | Transcribe audio files | `audio_path`, `model`, `language` |
| `generate_image` | Generate images with Gemini | `prompt`, `output_path` |
| `google_ocr` | Extract text with Google Vision | `input_file`, `file_type` |
| `wolfram_alpha` | Query Wolfram Alpha for computed and symbolic answers | `query`, `maxchars`, `units`, `assumption` |
| `send_ws_msg` | Send WhatsApp messages to any destination or default fallback | `destination` (optional), `message`, `template_name` (optional) |
| `get_ws_messages` | Fetch recent WhatsApp messages from webhook storage | `limit` (optional, default 10), `since` (optional, ISO 8601 timestamp) |
| `mp_create_checkout_link` | Create a Mercado Pago subscription checkout link | `phone_number`, `payer_email` (optional) |
| `mp_check_subscription` | Check Mercado Pago subscription status by preapproval ID | `subscription_id` |
| `mp_cancel_subscription` | Cancel a Mercado Pago subscription by preapproval ID | `subscription_id` |
| `mp_simulate_webhook` | Simulate a Mercado Pago webhook payload for testing | `payload` (JSON string) |

### WhatsApp Webhook Setup

To receive messages, you need to run the webhook server:

```bash
# Start the webhook server
python cli.py whatsapp-webhook --port 5000
```

Then configure in Meta Developer dashboard:

1. **Webhook URL:** `https://your-domain.com/webhook` (use ngrok for local testing)
2. **Verify Token:** Set in `WHATSAPP_WEBHOOK_VERIFY_TOKEN` env var
3. **Subscribe to fields:** `messages`

For local testing with ngrok:
```bash
# Terminal 1: Start webhook server
python cli.py whatsapp-webhook --port 5000

# Terminal 2: Expose via ngrok
ngrok http 5000
```

### Agent Skills
The project includes specialized Agent Skills for coding agents:

- **Research & Information Gathering**: `mcpjose-research`, `mcp-builder`
- **Document Creation & Manipulation**: `docx`, `pdf`, `pptx`, `xlsx`, `doc-coauthoring`
- **Design & Visual Content**: `frontend-design`, `canvas-design`, `algorithmic-art`, `theme-factory`
- **Web Development**: `web-artifacts-builder`, `webapp-testing`
- **Communication & Internal Tools**: `internal-comms`
- **Math & Computation**: `wolfram-alpha`
- **Meta Skills**: `skill-creator`
- **Connectors & Platforms**: `notion`, `linear`, `sentry`, `vercel-deploy`, `netlify-deploy`, `cloudflare-deploy`, `render-deploy`, `aspnet-core`, `winui-app`

## Development

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_search.py
pytest tests/test_whatsapp.py
pytest tests/test_mcp_tools.py
pytest tests/test_payment_gateway.py

# Run with verbose output
pytest -v
```

### Linting and Formatting

```bash
# Check code quality
ruff check .

# Format code
ruff format .
```

### Adding New Tools

1. Create a new module in `tools/` directory
2. Implement the tool following existing patterns
3. Register the tool in `mcp_server/server.py`
4. Add tests in `tests/`
5. Update CLI entry points in `cli.py` if needed
