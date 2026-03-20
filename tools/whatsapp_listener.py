"""Backward-compatible wrapper for the WhatsApp-only agent loop."""

from __future__ import annotations

from langchain_agent.whatsapp_runner import main


if __name__ == "__main__":
    raise SystemExit(main())
