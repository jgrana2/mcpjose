#!/usr/bin/env python3
"""Record audio from microphone for testing transcription."""

import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np
import sys
from pathlib import Path

def record_audio(duration=5, sample_rate=44100, output_file="test_recording.wav"):
    """
    Record audio from the default microphone.
    
    Args:
        duration: Recording duration in seconds (default: 5)
        sample_rate: Sample rate in Hz (default: 44100)
        output_file: Output file path (default: test_recording.wav)
    """
    print(f"Recording for {duration} seconds...")
    print("Speak now!")
    
    # Record audio
    recording = sd.rec(int(duration * sample_rate), 
                       samplerate=sample_rate, 
                       channels=1, 
                       dtype='int16')
    
    # Wait for recording to complete
    sd.wait()
    
    print("Recording complete!")
    
    # Save to WAV file
    output_path = Path(output_file)
    wavfile.write(output_path, sample_rate, recording)
    
    print(f"Saved to: {output_path.absolute()}")
    return str(output_path.absolute())

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Record audio from microphone")
    parser.add_argument("--duration", type=int, default=5, help="Recording duration in seconds")
    parser.add_argument("--output", default="test_recording.wav", help="Output file path")
    parser.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz")
    
    args = parser.parse_args()
    
    try:
        record_audio(args.duration, args.sample_rate, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
