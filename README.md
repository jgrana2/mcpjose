# MCP Jose

**MCP Jose** is a unified **MCP (Model Context Protocol) server** that exposes a comprehensive collection of AI-powered tools (vision, OCR, image generation, transcription, web search, messaging) behind a single server. This project enables AI assistants to interact with external services through a well-designed interface.

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
- **X/Twitter Search**: Search for tweets on specific topics
- **Content Extraction**: Read and process web pages and documents

### Messaging & Communication
- **WhatsApp Messaging**: Send messages via Meta WhatsApp Cloud API
- **Template Messages**: Support for WhatsApp template messages
- **Rate Limiting**: Built-in rate limiting for API calls

### Development & Agent Support
- **Agent Skills**: 15+ specialized skills for coding agents (document creation, design, web development, research)
- **LangChain Agent**: Dedicated LangChain tool-calling agent wired to project tools, skills, and `AGENTS.md`
- **CLI Interface**: Command-line tools for direct tool execution
- **Provider Pattern**: Clean abstraction for different AI service providers
- **Configuration Management**: Secure credential handling with singleton pattern

## Architecture

```
/
├── .agents/              # Agent Skills for enhanced capabilities
│   └── skills/          # Domain-specific knowledge modules
├── mcp_server/          # Main MCP server implementation
├── core/                # Core utilities and interfaces
│   ├── config.py       # Credential management
│   ├── utils.py        # Helper functions
│   └── rate_limit.py   # Rate limiting implementation
├── providers/           # AI provider implementations
│   ├── __init__.py     # Provider factory
│   └── search.py       # Search provider abstraction
├── tools/              # Individual tool modules
│   ├── navigation.py   # Web navigation tools
│   ├── whatsapp.py     # WhatsApp messaging tools
│   ├── search.py       # Search tools
│   └── filesystem.py   # File system tools
├── auth/               # Authentication handling
├── tests/              # Test suite
├── userapp/            # User application code
├── langchain_agent/    # LangChain agent integration package
└── cli.py              # CLI entry points
```

## Quick Start

### Prerequisites
- Python 3.8+
- API keys for services you plan to use (OpenAI, Google Cloud, etc.)

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
```

### Running the MCP Server

```bash
# Start the MCP server
python -m mcp_server.server

# The server will start and be ready to accept connections
```

### Using CLI Tools

```bash
# Get help with available CLI commands
python cli.py --help

# Call OpenAI LLM directly
python cli.py call-llm "Your prompt here"

# Process images with OpenAI Vision
python cli.py openai-vision image.jpg "Describe this image"

# Transcribe audio files
python cli.py transcribe-audio audio.mp3

# Generate images with Gemini
python cli.py generate-image "A beautiful sunset over mountains"

# Extract text with Google OCR
python cli.py google-ocr document.pdf

# Search the web
python cli.py search "latest AI developments"

# Send WhatsApp messages
python cli.py send-ws-msg "+1234567890" "Hello from MCP Jose!"
```

### Using the LangChain Agent

```bash
# List available tool wrappers
python -m langchain_agent.main --list-tools

# List discovered project skills (SKILL.md files)
python -m langchain_agent.main --list-skills

# Run a one-shot prompt
python -m langchain_agent.main "Use available skills and tools to research MCP updates"

# Run interactively
python -m langchain_agent.main --interactive
```

## Available Tools

### MCP Server Tools
The following tools are available when running the MCP server:

| Tool | Description | Parameters |
|------|-------------|------------|
| `search` | Search the web | `query`: Search query |
| `navigate_to_url` | Extract content from URLs | `url`: Target URL |
| `x_search` | Search X/Twitter | `topic`: Search topic |
| `call_llm` | Generate text with OpenAI | `prompt`: Text prompt |
| `openai_vision_tool` | Process images with OpenAI Vision | `image_path`, `prompt` |
| `transcribe_audio` | Transcribe audio files | `audio_path`, `model`, `language` |
| `generate_image` | Generate images with Gemini | `prompt`, `output_path` |
| `google_ocr` | Extract text with Google Vision | `input_file`, `file_type` |
| `send_ws_msg` | Send WhatsApp messages to any destination or default fallback | `destination` (optional), `message`, `template_name` (optional) |

### Agent Skills
The project includes 15+ specialized Agent Skills for coding agents:

- **Research & Information Gathering**: `mcpjose-research`, `mcp-builder`
- **Document Creation & Manipulation**: `docx`, `pdf`, `pptx`, `xlsx`, `doc-coauthoring`
- **Design & Visual Content**: `frontend-design`, `canvas-design`, `algorithmic-art`, `slack-gif-creator`, `theme-factory`
- **Web Development**: `web-artifacts-builder`, `webapp-testing`
- **Communication & Internal Tools**: `internal-comms`, `brand-guidelines`
- **Meta Skills**: `skill-creator`

Skills are automatically discovered from `.agents/skills/` and provide domain-specific knowledge, structured workflows, and best practices.

## Development

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_search.py
pytest tests/test_whatsapp.py
pytest tests/test_mcp_tools.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=.
```

### Linting and Formatting

```bash
# Check code quality
ruff check .

# Format code
ruff format .

# Check types (if type hints are used)
mypy .
```

### Adding New Tools

1. Create a new module in `tools/` directory
2. Implement the tool following existing patterns
3. Register the tool in `mcp_server/server.py`
4. Add tests in `tests/`
5. Update CLI entry points in `cli.py` if needed

### Adding New Providers

1. Implement interface from `core/interfaces.py`
2. Add to `providers/__init__.py` factory methods
3. Update configuration in `core/config.py` if needed

## API Requirements

### Required API Keys
Depending on which tools you use, you may need:

- **OpenAI API Key**: For vision, transcription, and LLM tools
- **Google Cloud Credentials**: For OCR and Gemini services
- **Meta WhatsApp API**: For WhatsApp messaging
- **Twitter/X API** (optional): For enhanced X search functionality

### Rate Limiting
The project includes rate limiting for WhatsApp messaging in `core/rate_limit.py` to prevent API abuse.

## Examples

### Using the MCP Server with Claude Desktop
1. Add the server to your Claude Desktop configuration:
```json
{
  "mcpServers": {
    "mcpjose": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "PYTHONPATH": "/path/to/mcpjose"
      }
    }
  }
}
```

2. Restart Claude Desktop
3. The tools will be available in your conversations

### Direct Python Usage
```python
from providers import ProviderFactory

# Create providers
vision = ProviderFactory.create_vision("openai")
ocr = ProviderFactory.create_ocr("google")
llm = ProviderFactory.create_llm("openai")

# Use providers
result = vision.process_image("image.jpg", "Describe this image")
text = ocr.extract_text("document.pdf")
response = llm.complete("Write a poem about AI")
```

## Project Structure Details

### Core Components
- **`core/config.py`**: Singleton credential manager with secure API key handling
- **`core/utils.py`**: Utility functions for file handling and common operations
- **`core/rate_limit.py`**: Rate limiting implementation for API calls

### Provider Pattern
All AI services use a provider abstraction:
```python
from providers import ProviderFactory

# Factory creates appropriate provider instances
provider = ProviderFactory.create_vision("openai")  # or "gemini"
```

### Tool Registration
Tools are registered in `mcp_server/server.py` and follow a consistent pattern:
- Each tool module has an `init_tools()` function
- Tools are added to the MCP server instance
- Error handling and input validation are built-in

## Security Considerations

### Never Commit Secrets
- Never commit `.env` files or credential files
- Never commit API keys, tokens, or passwords
- Use the credential manager for secure storage

### Input Validation
- All tools validate input parameters
- File paths are sanitized before use
- URL navigation includes safety checks

### Rate Limiting
- WhatsApp messaging has built-in rate limiting
- Consider adding rate limits for other APIs as needed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Run linting: `ruff check .`
6. Format code: `ruff format .`
7. Submit a pull request

### Pull Request Guidelines
- Include clear description of changes
- Add tests for new functionality
- Update documentation as needed
- Follow existing code patterns

## License

This project is available for use under appropriate licensing terms.

## Support

For issues and questions:
- Check the [AGENTS.md](AGENTS.md) file for agent-specific guidance
- Review existing tests for usage examples
- Check the `core/config.py` for configuration options

## Next Steps

- Explore the `userapp/` directory for example applications
- Check out the Agent Skills in `.agents/skills/` for specialized workflows
- Review the test suite for comprehensive usage examples
- Customize the configuration for your specific needs
