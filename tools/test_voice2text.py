#!/usr/bin/env python3
"""
Comprehensive test for the voice-to-text application.

This script tests the voice-to-text functionality with multiple speech recognition 
engines, recording audio and transcribing it with each engine.
"""

import os
import sys
import time
import tempfile
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger("voice2text_test")

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_engine(engine_name):
    """Test a specific speech recognition engine."""
    print(f"\n=== Testing {engine_name.title()} Engine ===")
    
    try:
        # Import the engine module dynamically
        if engine_name.lower() == "google":
            from engines.google import GoogleEngine
            engine = GoogleEngine()
        elif engine_name.lower() == "whisper":
            from engines.whisper import WhisperEngine
            engine = WhisperEngine()
        else:
            print(f"✗ Unknown engine: {engine_name}")
            return False
        
        print(f"✓ Successfully created {engine_name.title()} engine instance")
        
        # Import audio input for recording
        from core.audio_input import AudioInput
        audio_input = AudioInput()
        print(f"✓ Created audio input handler")
        
        # Record a short audio clip
        print("\nRecording 5 seconds of audio - please speak something...")
        audio_data = audio_input.capture_audio(duration=5.0, wait_for_speech=False)
        
        if audio_data is None:
            print("✗ Failed to capture audio")
            return False
        
        print(f"✓ Captured {len(audio_data)} bytes of audio data")
        
        # Save audio to a temporary file for debugging
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_data)
            print(f"✓ Saved audio to: {temp_file.name}")
        
        # Transcribe the audio
        print("\nTranscribing audio...")
        result = engine.recognize(audio_data)
        
        if result:
            print(f"✓ Transcription result: \"{result}\"")
            return True
        else:
            print("✗ Transcription failed or returned empty result")
            return False
            
    except Exception as e:
        print(f"✗ Error testing {engine_name} engine: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run tests for all engines."""
    print("=== Voice-to-Text Comprehensive Test ===")
    
    # Print Python information
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    
    # Test Google engine
    google_result = test_engine("google")
    
    # Test Whisper engine
    whisper_result = test_engine("whisper")
    
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