"""Terminal output helpers for the LangChain agent."""

from __future__ import annotations

import sys
from typing import TextIO

try:
    from rich.console import Console
    from rich.markdown import Markdown
except Exception:  # pragma: no cover - dependency guard
    Console = None
    Markdown = None


def print_markdown(text: str, *, output_stream: TextIO = sys.stdout) -> None:
    """Render Markdown to a terminal stream when possible."""
    rendered_text = str(text)

    is_tty = False
    isatty = getattr(output_stream, "isatty", None)
    if callable(isatty):
        try:
            is_tty = bool(isatty())
        except Exception:
            is_tty = False

    if Console is None or Markdown is None or not is_tty:
        print(rendered_text, file=output_stream)
        return

    console = Console(
        file=output_stream,
        force_terminal=True,
        soft_wrap=True,
        highlight=False,
    )
    console.print(Markdown(rendered_text))


def print_separator(*, output_stream: TextIO = sys.stdout, width: int = 80, char: str = "-") -> None:
    """Print a full-width separator line in terminal output."""
    line = char * max(width, 1)
    print(line, file=output_stream)
