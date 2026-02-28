#!/usr/bin/env python3
"""CLI entry point for Google OCR."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from cli import google_ocr_main

google_ocr_main()
