#!/usr/bin/env python3
"""
Audio transcription using OpenAI Whisper.

Usage:
    python -m tools.transcription.transcribe_audio <audio_path> [options]
    
Examples:
    # Basic transcription
    python -m tools.transcription.transcribe_audio audio.mp3
    
    # With language and timestamps
    python -m tools.transcription.transcribe_audio audio.mp3 --language en --timestamps
    
    # Save to file with context hint
    python -m tools.transcription.transcribe_audio audio.mp3 --prompt "Technical discussion about AI" --output transcript.txt
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add project root to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    
    from cli import transcribe_audio_main
    
    transcribe_audio_main()
