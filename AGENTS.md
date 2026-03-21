# AGENTS.md

This file helps coding agents work effectively with the MCP Jose project.

## Project Overview

**MCP Jose** is a unified MCP (Model Context Protocol) server providing AI-powered tools including:
- Vision processing (OpenAI and Gemini)
- OCR (Google Cloud Vision)
- Image generation (Gemini)
- Audio transcription (OpenAI Whisper)
- Web search and navigation
- WhatsApp messaging

### Architecture

```
/                   # Root
├── .agents/        # Agent Skills for enhanced capabilities
├── mcp_server/     # Main MCP server implementation
├── core/           # Core utilities and interfaces
├── providers/      # AI provider implementations
├── tools/          # Individual tool modules
├── auth/           # Authentication handling
├── tests/          # Test suite
├── userapp/        # User application code
└── cli.py          # CLI entry points
```

## Agent Skills

This project includes **Agent Skills** (https://agentskills.io) in the `.agents/skills/` directory. These are domain-specific knowledge modules that help AI coding agents perform specialized tasks with best practices and structured workflows.

### Available Skills

#### 🔍 Research & Information Gathering
- **mcpjose-research**: Workflow for web research, reading URLs/PDFs, and searching X/Twitter using this repo's MCP server tools (`search`, `navigate_to_url`, `x_search`)
- **mcp-builder**: Comprehensive guide for creating high-quality MCP servers with external API integrations

#### 📄 Document Creation & Manipulation
- **docx**: Create, read, edit, and manipulate Word documents (.docx) with formatting, tables, images, and tracked changes
- **pdf**: Read, extract, combine, split, watermark, encrypt, and OCR PDF files
- **pptx**: Create, read, and edit PowerPoint presentations with layouts, templates, and speaker notes
- **xlsx**: Create, read, edit spreadsheet files (.xlsx, .xlsm, .csv, .tsv) with formulas, formatting, and charts
- **doc-coauthoring**: Structured workflow for co-authoring technical documentation, proposals, specs, and decision docs

#### 🎨 Design & Visual Content
- **frontend-design**: Create distinctive, production-grade frontend interfaces with high design quality, avoiding generic AI aesthetics
- **canvas-design**: Create beautiful visual art in .png and .pdf documents using design philosophy
- **algorithmic-art**: Create algorithmic art using p5.js with seeded randomness, flow fields, and particle systems
- **theme-factory**: Apply 10 pre-set themes or generate custom themes for artifacts (slides, docs, HTML pages)

#### 🌐 Web Development
- **web-artifacts-builder**: Build complex, multi-component HTML artifacts using React, Tailwind CSS, and shadcn/ui
- **webapp-testing**: Interact with and test local web applications using Playwright (screenshots, UI testing, browser logs)

#### 📊 Communication & Internal Tools
- **internal-comms**: Write internal communications (status reports, leadership updates, newsletters, FAQs, incident reports)

#### 🛠️ Meta Skills
- **skill-creator**: Create new skills, modify existing skills, run evaluations, and optimize skill performance

### How to Use Skills

Skills are automatically discovered from `.agents/skills/` by compatible AI coding agents. Each skill provides:
- **Specialized knowledge**: Domain-specific best practices and patterns
- **Structured workflows**: Step-by-step processes for complex tasks
- **Tool integration**: Guidance on using relevant tools effectively
- **Output standards**: Quality expectations and formatting guidelines

When working with documents, visual content, web development, or research tasks, agents will automatically leverage the appropriate skill to deliver better results.

## Build and Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or activate environment
source env/bin/activate
```

### Running the Server
```bash
# Run the MCP server
python -m mcp_server.server

# Or use the CLI entry points
python cli.py --help
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_mcp_tools.py
pytest tests/test_refactored.py
pytest tests/test_search.py

# Run with verbose output
pytest -v
```

### Linting
```bash
# Code formatting and linting (uses ruff)
ruff check .
ruff format .
```

## Code Style Guidelines

### Python Style
- **Formatter**: Use `ruff` for linting and formatting
- **Line length**: 100 characters maximum
- **Quotes**: Double quotes for strings
- **Imports**: Group imports (stdlib, third-party, local) with blank lines between groups

### Naming Conventions
- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `lowercase_with_underscores`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private**: Prefix with underscore `_private_method`

### Code Patterns
- Use type hints where appropriate
- Prefer dependency injection via the `ProviderFactory`
- Follow the interface pattern defined in `core/interfaces.py`
- Handle errors gracefully with try/except blocks

## Project-Specific Guidelines

### Provider Pattern
All AI services are implemented via the provider pattern:

```python
from providers import ProviderFactory

# Create providers using the factory
vision = ProviderFactory.create_vision("openai")
ocr = ProviderFactory.create_ocr("google")
llm = ProviderFactory.create_llm("openai")
```

### Adding New Tools
1. Create a new module in `tools/` directory
2. Implement the tool following existing patterns
3. Register the tool in `mcp_server/server.py`
4. Add tests in `tests/`

### Environment Variables
The project uses a credential management system in `core/config.py`. Key environment variables:
- API keys for OpenAI, Gemini, Google Cloud
- WhatsApp credentials
- Database connections (SQLite)

Never commit credentials or `.env` files. Use the credential manager for secure storage.

### Database
- Uses SQLite for the twscrape library (`accounts.db` in root)

### User application
- All user created applications are in `userapp/`

## Testing Instructions

### Test Structure
- Tests are in `tests/` directory
- Naming: `test_*.py` files with `test_*` functions
- Uses `pytest` framework

### Running Tests
```bash
# All tests
pytest

# With coverage (if configured)
pytest --cov=.

# Specific test
pytest tests/test_search.py::test_search_function -v
```

### Writing Tests
- Use descriptive test names
- Mock external API calls
- Test both success and error cases
- Use fixtures for setup/teardown

## Security Considerations

### Critical Rules
1. **NEVER commit secrets** - API keys, credentials, tokens
2. **NEVER log sensitive data** - API keys, passwords, personal data
3. **Validate all inputs** - Sanitize user inputs before processing
4. **Rate limiting** - The project has rate limiting for WhatsApp messaging in `core/rate_limit.py`

### Sensitive Files (Never commit)
- `.env` files
- `*.key`, `*.pem` files
- `credentials.json`
- Database files (`.db`)

### API Key Handling
```python
from core.config import CredentialManager

creds = CredentialManager()
api_key = creds.get_api_key("openai")  # Secure retrieval
```

## Pull Request Guidelines

### Before Submitting
1. Run all tests: `pytest`
2. Run linting: `ruff check .`
3. Format code: `ruff format .`
4. Update relevant documentation
5. Add tests for new functionality

### PR Description
Include:
- What changed and why
- How to test the changes
- Any breaking changes
- Related issues

## Common Tasks

### Adding a New Provider
1. Implement interface from `core/interfaces.py`
2. Add to `providers/__init__.py` factory methods
3. Update configuration in `core/config.py` if needed

### Adding a New Tool
1. Create module in `tools/`
2. Implement tool logic
3. Register in `mcp_server/server.py`
4. Add CLI entry point in `cli.py` if needed
5. Write tests

### Debugging
- Check `core/utils.py` for helper functions
- Use the credential manager for API configuration issues
- Review rate limit logs if hitting API limits

## External Dependencies

Key packages (see `requirements.txt`):
- `mcp` - Model Context Protocol SDK
- `openai` - OpenAI API client
- `google-genai`, `google-cloud-vision` - Google AI services
- `vertexai` - Google Vertex AI
- `python-dotenv` - Environment management
- `ddgs` - DuckDuckGo search

## WhatsApp Image Size Limits

When sending images via WhatsApp (`send_ws_msg` tool):
- Large images (>5MB) will fail with error #100 (Invalid parameter)
- AI-generated PNGs can be 5-10MB; resize before sending
- Use ImageMagick: `magick image.png -resize 30% -quality 80 image.jpg`
- See `.agents/skills/send-ws-msg/SKILL.md` for detailed optimization guidance

## Questions?

When in doubt:
1. Check existing implementations in similar modules
2. Follow the established patterns
3. Prioritize security and error handling
4. Write tests for new functionality
5. Ask the user multiple choice questions for clarification
