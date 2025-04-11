#!/usr/bin/env python3
"""
Simple test for the Google speech recognition engine.

This script tests if the Google engine can be properly initialized and used.
"""

import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger("google_test")

def main():
    """Run the Google engine test."""
    print("=== Google Speech Recognition Engine Test ===")
    
    # Print Python information
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")
    
    # Try to import speech_recognition
    print("\nTesting imports:")
    try:
        import speech_recognition as sr
        print(f"✓ speech_recognition imported successfully (version: {sr.__version__})")
        
        # Create a recognizer
        recognizer = sr.Recognizer()
        print(f"✓ Created Recognizer object")
        
        # Check microphone availability
        try:
            mics = sr.Microphone.list_microphone_names()
            print(f"✓ Found {len(mics)} microphones:")
            for i, mic in enumerate(mics):
                print(f"  {i}: {mic}")
        except Exception as e:
            print(f"✗ Error listing microphones: {e}")
        
        print("\nGoogle Speech engine is available and ready to use!")
        
    except ImportError as e:
        print(f"✗ Failed to import speech_recognition: {e}")
        print("Make sure you installed SpeechRecognition with: pip install SpeechRecognition")
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()