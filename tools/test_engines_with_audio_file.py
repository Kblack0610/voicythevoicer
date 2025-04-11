#!/usr/bin/env python3
"""
Test speech recognition engines with a pre-recorded WAV file.

This script tests the Google and Whisper speech recognition engines
using a pre-recorded WAV file to verify transcription functionality.
"""

import os
import sys
import time
import wave
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger("engine_test")

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def read_wav_file(file_path):
    """Read audio data from a WAV file."""
    with wave.open(file_path, 'rb') as wav_file:
        # Get basic information
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        # Read all frames
        audio_data = wav_file.readframes(n_frames)
        
        print(f"WAV file info:")
        print(f"  Channels: {n_channels}")
        print(f"  Sample width: {sample_width} bytes")
        print(f"  Frame rate: {frame_rate} Hz")
        print(f"  Number of frames: {n_frames}")
        print(f"  Duration: {n_frames / frame_rate:.2f} seconds")
        print(f"  Size: {len(audio_data)} bytes")
        
        return audio_data, frame_rate

def test_google_engine(audio_data):
    """Test the Google speech recognition engine."""
    print("\n=== Testing Google Speech Recognition Engine ===")
    
    try:
        from engines.google import GoogleEngine
        engine = GoogleEngine()
        print(f"✓ Successfully created Google engine instance")
        
        # Transcribe the audio
        print("\nTranscribing audio with Google...")
        result = engine.recognize(audio_data)
        
        if result:
            print(f"✓ Transcription result: \"{result}\"")
            return True
        else:
            print("✗ Transcription failed or returned empty result")
            return False
            
    except Exception as e:
        print(f"✗ Error testing Google engine: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_whisper_engine(audio_data):
    """Test the Whisper speech recognition engine."""
    print("\n=== Testing Whisper Speech Recognition Engine ===")
    
    try:
        from engines.whisper import WhisperEngine
        engine = WhisperEngine()
        print(f"✓ Successfully created Whisper engine instance")
        
        # Transcribe the audio
        print("\nTranscribing audio with Whisper...")
        result = engine.recognize(audio_data)
        
        if result:
            print(f"✓ Transcription result: \"{result}\"")
            return True
        else:
            print("✗ Transcription failed or returned empty result")
            return False
            
    except Exception as e:
        print(f"✗ Error testing Whisper engine: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test speech recognition engines with a WAV file."""
    print("=== Speech Recognition Engine Test with WAV File ===")
    
    # Define the path to the WAV file
    wav_file = "/tmp/test_recording.wav"
    
    if not os.path.exists(wav_file):
        print(f"✗ WAV file not found: {wav_file}")
        print("Please run tools/test_audio_capture.py first to create the test_recording.wav file.")
        return 1
    
    # Read the WAV file
    print(f"\nReading WAV file: {wav_file}")
    audio_data, frame_rate = read_wav_file(wav_file)
    
    # Test Google engine
    google_result = test_google_engine(audio_data)
    
    # Test Whisper engine
    whisper_result = test_whisper_engine(audio_data)
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Google Engine: {'✓ Passed' if google_result else '✗ Failed'}")
    print(f"Whisper Engine: {'✓ Passed' if whisper_result else '✗ Failed'}")
    
    if google_result or whisper_result:
        print("\n✓ Voice-to-text functionality is working with at least one engine!")
        return 0
    else:
        print("\n✗ All engines failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())