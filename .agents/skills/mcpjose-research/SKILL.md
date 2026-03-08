---
name: mcpjose-research
description: Use for web research, reading URLs/PDFs, or searching X/Twitter using the mcpjose MCP server tools (search, navigate_to_url, x_search). Avoid for purely offline coding tasks.
---

# mcpjose-research

This skill provides a repeatable workflow for doing online research with the MCP tools exposed by this repository.

## Tools

See `references/mcpjose-tools.md` for a compact list of available tools and behavior notes.

## Workflow

1) Choose the right starting tool

- Use `search(query=...)` to discover sources and pick URLs.
- Use `navigate_to_url(url=...)` to extract readable content from a specific page or PDF.
- Use `x_search(topic=...)` include for online conversation context (or you need "what people are saying").

2) Web research loop (recommended default)

- Run `search` with a specific query.
- Pick 2-5 results (prefer primary docs).
- For each selected result, run `navigate_to_url` and extract only the key parts.
- Synthesize an answer. Include a short "Sources" list with URLs.

3) X/Twitter search loop (include online conversations context)

- Keep the query short and specific (2-3 keywords).
- Run `x_search(topic=...)`.
- Summarize themes; do not treat tweets as authoritative facts.
- If `x_search` fails due to missing credentials, fall back to `search` for web sources about the topic.

4) PDF handling

- Use `navigate_to_url` on the PDF URL; it supports PDFs and returns extracted text.
- Prefer summarizing by section/page; avoid copying full PDFs into the final response.

## Output expectations

- Provide a concise, structured result.
- Link to sources; do not dump large tool outputs.
