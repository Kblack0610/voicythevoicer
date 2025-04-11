#!/usr/bin/env python3
"""
Simple test for the Whisper engine.

This script tests the local Whisper engine by recording a short audio clip and
trying to transcribe it.
"""

import os
import sys
import time
import logging

# Add the parent directory to path for module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger("whisper_test")

# Import core modules
from core.audio_input import AudioInput, AudioConfig
from engines.whisper import WhisperEngine


def main():
    """Run the Whisper engine test."""
    print("=== Whisper Engine Test ===")
    
    # Initialize audio input
    print("\nInitializing audio input...")
    audio_config = AudioConfig(
        sample_rate=16000,
        channels=1,
        chunk_size=1024,
        format="int16",  # 16-bit PCM
        vad_enabled=True
    )
    audio_input = AudioInput(audio_config)
    
    # Initialize Whisper engine
    print("\nInitializing Whisper engine...")
    engine = WhisperEngine(model_name="tiny")
    print(f"Using engine: {engine.get_name()}")
    
    # Record audio
    print("\nRecording 5 seconds of audio...")
    print("Please speak now...")
    audio_data = audio_input.capture_audio(duration=5.0, wait_for_speech=True)
    
    if audio_data:
        print(f"Recorded {len(audio_data)} bytes of audio data")
        
        # Transcribe audio
        print("\nTranscribing with Whisper...")
        start_time = time.time()
        text = engine.recognize(audio_data)
        end_time = time.time()
        
        print(f"Transcription time: {end_time - start_time:.2f} seconds")
        
        if text:
            print(f"\nTranscription: \"{text}\"")
        else:
            print("\nNo speech detected or transcription failed.")
    else:
        print("Failed to record audio.")
    
    print("\nTest complete.")


if __name__ == "__main__":
    main()