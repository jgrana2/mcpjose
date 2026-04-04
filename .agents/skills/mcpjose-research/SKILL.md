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

2a) Recency-first queries (when user says "latest", "new", "recent", "this year", "current")

- CRITICAL: NEVER append prior years like "2024" or "2025" to your search queries. Always use the absolute current year (2026) to ensure true recency.
- Default interpretation: "this year" or "current" = current calendar year (2026); "latest" = strictly search for the current year. DO NOT fallback to the last 12 months or append previous years (e.g., 2024, 2025) unless explicitly instructed.
- Start with time-bounded queries (add the year and/or month): e.g. `"<brand>" "<product line>" 2026`, `site:<brand-domain> <product> 2026`, `<event> 2026 <brand> <product>`.
- Prefer primary sources for the final list:
  - Official product pages (e.g. `site:<brand-domain>/<product-slug-prefix>`)
  - Official news/press posts if available
  - Reputable industry press for announcement dates/pricing when official pages lack dates
- If results are missing or noisy, pivot queries rather than broadening time:
  - Add a specific model keyword (e.g. `"<model name>"`)
  - Use `site:` constraints for manufacturer + 1-2 major outlets
  - STRICTLY MAINTAIN the current year constraint. Do not revert to past years.

2b) Product-page discovery pattern (for "list models" requests)

- Run a targeted `site:` search for the brand's product URL pattern (common for music gear brands):
  - Example: `site:<brand-domain> <product-slug-prefix>` and `site:<brand-domain> "<product line>" "Discover"`
- Open likely product pages and collection pages with `navigate_to_url`.
- Cross-check the product name with at least one independent source when launch timing matters.

3) X/Twitter search loop (include online conversations context)

- Keep the query short and specific (2-3 keywords).
- Run `x_search(topic=...)`.
- Summarize themes; do not treat tweets as authoritative facts.
- If `x_search` fails due to missing credentials, fall back to `search` for web sources about the topic.

4) PDF handling

- Use `navigate_to_url` on the PDF URL; it supports PDFs and returns extracted text.
- Prefer summarizing by section/page; avoid copying full PDFs into the final response.

## Output expectations

- Provide a concise, structured result (lead with the newest items first).
- Link to sources; do not dump large tool outputs.

## Ambiguity handling (minimize token waste)

- If the user's wording is ambiguous and could change the answer materially (e.g. "latest" could mean "this year" vs "last 5 releases"), do a quick recency-first pass (current year) and answer immediately.
- Only ask a clarification question if the recency-first pass yields zero credible results.
