#!/usr/bin/env python3
"""
Simple test for the Whisper speech recognition engine.

This script tests if the Whisper engine can be properly initialized and used.
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

logger = logging.getLogger("whisper_test")

def main():
    """Run the Whisper engine test."""
    print("=== OpenAI Whisper Engine Test ===")
    
    # Print Python information
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")
    
    # Try to import whisper
    print("\nTesting imports:")
    try:
        import whisper
        print(f"✓ whisper imported successfully (version: {getattr(whisper, '__version__', 'unknown')})")
        
        # List available models
        print(f"✓ Available models: {whisper.available_models()}")
        
        # Try to load the smallest model
        print(f"\nLoading tiny model (this may take a moment)...")
        model = whisper.load_model("tiny")
        print(f"✓ Successfully loaded tiny model")
        
        print("\nWhisper engine is available and ready to use!")
        
    except ImportError as e:
        print(f"✗ Failed to import whisper: {e}")
        # Check if the module exists in site-packages
        site_packages = next((p for p in sys.path if p.endswith('site-packages')), None)
        if site_packages:
            whisper_path = os.path.join(site_packages, 'whisper')
            openai_whisper_path = os.path.join(site_packages, 'openai_whisper')
            
            print(f"\nChecking for module files:")
            for path, name in [(whisper_path, 'whisper'), (openai_whisper_path, 'openai_whisper')]:
                if os.path.exists(path):
                    print(f"✓ {name} directory exists at: {path}")
                    print(f"  Contents: {os.listdir(path)}")
                else:
                    print(f"✗ {name} directory not found at: {path}")
        
        print("\nMake sure you installed openai-whisper with: pip install openai-whisper")
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()