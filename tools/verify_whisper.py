#!/usr/bin/env python3
"""
Verify that the Whisper module can be imported correctly.
"""

import sys
import os
import importlib.util

def check_module(module_name):
    """Check if a module can be imported and report its location."""
    print(f"Checking for module: {module_name}")
    
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            print(f"✓ Module {module_name} found!")
            if spec.origin:
                print(f"  Location: {spec.origin}")
            return True
        else:
            print(f"✗ Module {module_name} not found.")
            return False
    except ImportError as e:
        print(f"✗ Error checking for {module_name}: {e}")
        return False

def main():
    print("=== Python Import Path ===")
    for path in sys.path:
        print(f"  {path}")
    
    print("\n=== Module Availability Check ===")
    modules_to_check = [
        "openai-whisper",
        "openai_whisper",
        "whisper",
        "faster_whisper",
        "speech_recognition",
        "pyaudio"
    ]
    
    for module in modules_to_check:
        check_module(module)
        print()
    
    # Try to import and use whisper directly
    print("Attempting to import and use whisper module directly:")
    try:
        import whisper
        print(f"✓ Successfully imported whisper module")
        print(f"✓ Available models: {whisper.available_models()}")
        print(f"✓ Whisper version: {whisper.__version__ if hasattr(whisper, '__version__') else 'unknown'}")
    except ImportError as e:
        print(f"✗ Failed to import whisper: {e}")
    except Exception as e:
        print(f"✗ Error using whisper: {type(e).__name__}: {e}")
    
if __name__ == "__main__":
    main()