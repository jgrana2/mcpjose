"""Re-export and extend terminal output helpers for deep agent CLI."""

from __future__ import annotations

import sys
from typing import TextIO

from langchain_agent.terminal_output import print_markdown, print_separator

__all__ = [
    "print_markdown",
    "print_separator",
    "print_info",
    "print_success",
    "print_warning",
    "print_error",
    "print_debug",
]


def print_info(text: str, *, output_stream: TextIO = sys.stdout) -> None:
    """Print an info message (blue)."""
    print(f"ℹ️  {text}", file=output_stream)


def print_success(text: str, *, output_stream: TextIO = sys.stdout) -> None:
    """Print a success message (green)."""
    print(f"{text}", file=output_stream)


def print_warning(text: str, *, output_stream: TextIO = sys.stdout) -> None:
    """Print a warning message (yellow)."""
    print(f"⚠️  {text}", file=output_stream)


def print_error(text: str, *, output_stream: TextIO = sys.stderr) -> None:
    """Print an error message (red)."""
    print(f"❌ {text}", file=output_stream)


def print_debug(text: str, *, output_stream: TextIO = sys.stdout) -> None:
    """Print a debug message (dim)."""
    print(f"  → {text}", file=output_stream)
