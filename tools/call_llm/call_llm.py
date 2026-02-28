#!/usr/bin/env python3
"""CLI entry point for OpenAI LLM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cli import call_llm_main

call_llm_main()
