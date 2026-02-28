#!/usr/bin/env python3
"""CLI entry point for Gemini Vision."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from cli import gemini_vision_main

gemini_vision_main()
