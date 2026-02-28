#!/usr/bin/env python3
"""CLI entry point for OpenAI Vision."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from cli import openai_vision_main

openai_vision_main()
