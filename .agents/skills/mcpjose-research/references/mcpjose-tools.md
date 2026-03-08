# mcpjose MCP tools (quick reference)

This skill is designed to work with the MCP server defined in `mcp_server/server.py`.

## Research tools

- `search(query: str) -> { results?: [{title,url,snippet}], error?: str }`
  - Uses `SEARCH_ENGINE` env var (`ddgs` or `pse`).

- `navigate_to_url(url: str) -> { content?: str, url: str, type?: "html"|"pdf", error?: str }`
  - Extracts readable text from HTML pages; for PDFs it extracts per-page text.

- `x_search(topic: str) -> { text: str, count: int, topic: str, search_query: str }`
  - Deterministic keyword matching; best with 2-3 keywords.
  - Requires TwScrape env vars to be configured; may raise if missing.

## Optional AI helpers (available only if credentials are configured)

- `call_llm(prompt: str) -> { text: str }`
- `openai_vision_tool(image_path: str, prompt: str, ...) -> { text: str }`
- `gemini_vision_tool(image_path: str, prompt: str, ...) -> { text: str }`
- `google_ocr(input_file: str, ...) -> { annotations: [...], output_path?: str }`
- `generate_image(prompt: str, ...) -> { text?: str, image_path?: str }`
