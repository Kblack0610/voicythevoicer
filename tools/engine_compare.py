#!/usr/bin/env python3
"""
Engine Comparison Tool.

This script allows you to compare the performance of different speech 
recognition engines by recording audio and processing it with multiple engines.
"""

import os
import sys
import time
import argparse
import yaml
import logging
from typing import Dict, Any, List
from tabulate import tabulate

# Add parent directory to path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(script_dir)

from core.audio_input import AudioInput
from core.engines import EngineRegistry
from core.error_handlers import ErrorSuppressor


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare speech recognition engines"
    )
    parser.add_argument(
        "--engines", 
        type=str,
        nargs='+',
        help="Engines to compare (e.g., 'google whisper deepgram')"
    )
    parser.add_argument(
        "--duration", 
        type=float,
        default=5.0,
        help="Duration of audio to record in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--wait", 
        action="store_true",
        help="Wait for speech to start before recording"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(script_dir, "config.yaml"),
        help="Path to config file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def init_engines(engine_names: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize specified engines."""
    engines = {}
    
    for name in engine_names:
        if name in EngineRegistry.list_engines():
            try:
                # Get engine config if available
                engine_config = config.get(name, {})
                
                # Create engine instance
                engine = EngineRegistry.get_engine(name, **engine_config)
                engines[name] = {
                    "instance": engine,
                    "name": engine.get_name(),
                    "latency": engine.get_latency_profile()
                }
                print(f"Initialized engine: {engine.get_name()}")
            except Exception as e:
                print(f"Failed to initialize engine '{name}': {e}")
        else:
            print(f"Engine '{name}' not found. Available engines: {', '.join(EngineRegistry.list_engines())}")
    
    return engines


def record_audio(duration: float, wait_for_speech: bool, config: Dict[str, Any]) -> bytes:
    """Record audio from microphone."""
    try:
        # Get audio config
        audio_config = config.get("audio", {})
        
        # Create audio input
        with ErrorSuppressor.suppress_stderr():
            audio_input = AudioInput(**audio_config)
        
        print(f"Recording audio{' (waiting for speech)' if wait_for_speech else ''}...")
        
        # Record audio
        audio_data = audio_input.capture_audio(
            duration=duration,
            wait_for_speech=wait_for_speech
        )
        
        if audio_data:
            print(f"Recorded {len(audio_data)} bytes of audio")
            return audio_data
        else:
            print("Failed to record audio")
            return b''
    except Exception as e:
        print(f"Error recording audio: {e}")
        return b''


def run_comparison(engines: Dict[str, Any], audio_data: bytes) -> List[Dict[str, Any]]:
    """Run comparison of engines with the same audio data."""
    results = []
    
    for name, engine_info in engines.items():
        engine = engine_info["instance"]
        
        try:
            print(f"Processing with {engine.get_name()}...")
            
            # Measure start time
            start_time = time.time()
            
            # Recognize speech
            text = engine.recognize(audio_data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            results.append({
                "engine": name,
                "name": engine.get_name(),
                "text": text or "(No text recognized)",
                "processing_time": processing_time,
                "success": text is not None,
                "latency_category": engine_info["latency"].get("latency_category", "unknown")
            })
            
            print(f"Result: {text or '(No text recognized)'}")
            print(f"Processing time: {processing_time:.2f}s")
            print()
            
        except Exception as e:
            print(f"Error processing with {engine.get_name()}: {e}")
            results.append({
                "engine": name,
                "name": engine.get_name(),
                "text": f"ERROR: {str(e)}",
                "processing_time": 0,
                "success": False,
                "latency_category": "error"
            })
    
    return results


def display_results(results: List[Dict[str, Any]]):
    """Display comparison results in a table."""
    if not results:
        print("No results to display")
        return
    
    # Sort by processing time
    results.sort(key=lambda x: x["processing_time"])
    
    # Prepare table
    table_data = []
    for r in results:
        table_data.append([
            r["name"],
            "✓" if r["success"] else "✗",
            f"{r['processing_time']:.2f}s",
            r["latency_category"],
            r["text"][:80] + ("..." if len(r["text"]) > 80 else "")
        ])
    
    # Print table
    headers = ["Engine", "Success", "Time", "Latency", "Recognized Text"]
    print("\nResults:")
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))


def main():
    """Main function."""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Load configuration
    config = load_config(args.config)
    
    # Get engines to compare
    if args.engines:
        engine_names = args.engines
    else:
        engine_names = EngineRegistry.list_engines()
        
        # If too many engines, limit to the most common ones
        if len(engine_names) > 3:
            default_engines = ["google", "whisper", "deepgram"]
            engine_names = [e for e in default_engines if e in engine_names]
            
            if not engine_names:
                engine_names = EngineRegistry.list_engines()[:3]
    
    print(f"Comparing engines: {', '.join(engine_names)}")
    
    # Initialize engines
    engines = init_engines(engine_names, config)
    
    if not engines:
        print("No engines available for comparison")
        return
    
    # Record audio
    audio_data = record_audio(
        duration=args.duration,
        wait_for_speech=args.wait,
        config=config
    )
    
    if not audio_data:
        print("No audio data to process")
        return
    
    # Run comparison
    results = run_comparison(engines, audio_data)
    
    # Display results
    display_results(results)


if __name__ == "__main__":
    with ErrorSuppressor.suppress_stderr():
        main()