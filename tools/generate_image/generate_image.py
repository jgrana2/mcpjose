#!/usr/bin/env python3
"""CLI entry point for image generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from cli import generate_image_main

generate_image_main()
