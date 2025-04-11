#!/usr/bin/env python3
"""
Engine Availability Checker.

This script checks which speech recognition engines are available and properly registered.
"""

import os
import sys
import importlib

# Add parent directory to path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(script_dir)

# Import without suppressing errors to see what's happening
from core.engines import EngineRegistry

# Try importing each engine directly with detailed error reporting
engine_modules = ['google', 'whisper', 'deepgram', 'groq', 'speechmatics']

print("\n=== Engine Availability Check ===\n")

# First, check which engines we can import directly
print("Checking engine imports:")
for module_name in engine_modules:
    try:
        # Print import path
        full_path = os.path.join(script_dir, "engines", f"{module_name}.py")
        print(f"\n{module_name} (path: {full_path}):")
        
        # Try importing
        module = importlib.import_module(f"engines.{module_name}")
        print(f"  Import: SUCCESS")
        
        # Check if the module has the expected class
        class_name = f"{module_name.capitalize()}Engine"
        if hasattr(module, class_name):
            print(f"  {class_name} class: FOUND")
        else:
            print(f"  {class_name} class: NOT FOUND")
            
    except ImportError as e:
        print(f"  Import failed: {e}")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")

# Now check which engines are actually registered
print("\nRegistered engines:")
engines = EngineRegistry.list_engines()
if engines:
    for name in engines:
        try:
            engine = EngineRegistry.get_engine(name)
            print(f"  {name}: {engine.get_name() if engine else 'Failed to initialize'}")
        except Exception as e:
            print(f"  {name}: Error initializing - {type(e).__name__}: {e}")
else:
    print("  No engines registered!")

# Print the import paths that Python is searching
print("\nPython import paths:")
for path in sys.path:
    print(f"  {path}")

print("\nDone.")