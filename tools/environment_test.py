#!/usr/bin/env python3
"""
Environment Testing Tool.

This script tests the Voice2Text system in different environments and applications,
checking for compatibility and performance issues.
"""

import os
import sys
import time
import subprocess
import platform
import argparse
import logging
from typing import Dict, Any, List

# Add parent directory to path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(script_dir)

from core.audio_input import AudioInput
from core.text_output import TextOutput
from core.engine_selector import EngineSelector
from core.error_handlers import ErrorSuppressor


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Voice2Text in different environments"
    )
    parser.add_argument(
        "--applications",
        type=str,
        nargs="+",
        help="Applications to test (e.g., 'gedit firefox terminal')",
        default=["terminal"]
    )
    parser.add_argument(
        "--test-phrase",
        type=str,
        default="This is a test of the voice to text system",
        help="Phrase to use for testing (if not recording)"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record audio instead of using test phrase"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Duration to record audio (if recording)"
    )
    parser.add_argument(
        "--engine",
        type=str,
        help="Engine to use (default: auto-select)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


def check_system_info():
    """Get system information."""
    system_info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "distribution": "",
        "desktop_env": os.environ.get("XDG_CURRENT_DESKTOP", "Unknown"),
        "audio_output": "",
        "audio_input": "",
        "python_version": platform.python_version(),
    }
    
    # Get Linux distribution if applicable
    if system_info["os"] == "Linux":
        try:
            import distro
            system_info["distribution"] = distro.name(pretty=True)
        except ImportError:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            system_info["distribution"] = line.split("=")[1].strip().strip('"')
                            break
    
    # Get audio subsystem info on Linux
    if system_info["os"] == "Linux":
        try:
            # Check for ALSA devices
            alsa_output = subprocess.check_output(["arecord", "-l"], stderr=subprocess.DEVNULL)
            system_info["audio_input"] = "ALSA"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        try:
            # Check for PulseAudio
            pulse_output = subprocess.check_output(["pactl", "info"], stderr=subprocess.DEVNULL)
            system_info["audio_output"] = "PulseAudio"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        try:
            # Check for PipeWire
            pipewire_output = subprocess.check_output(["pw-cli", "info"], stderr=subprocess.DEVNULL)
            system_info["audio_output"] = "PipeWire"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    return system_info


def check_audio_devices():
    """Check for available audio devices."""
    with ErrorSuppressor.suppress_stderr():
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            input_devices = []
            output_devices = []
            
            for i in range(p.get_device_count()):
                dev_info = p.get_device_info_by_index(i)
                
                if dev_info["maxInputChannels"] > 0:
                    input_devices.append({
                        "index": i,
                        "name": dev_info["name"],
                        "channels": dev_info["maxInputChannels"],
                        "sample_rate": dev_info["defaultSampleRate"]
                    })
                
                if dev_info["maxOutputChannels"] > 0:
                    output_devices.append({
                        "index": i,
                        "name": dev_info["name"],
                        "channels": dev_info["maxOutputChannels"],
                        "sample_rate": dev_info["defaultSampleRate"]
                    })
            
            p.terminate()
            
            return {
                "input_devices": input_devices,
                "output_devices": output_devices,
                "default_input": p.get_default_input_device_info()["index"] if p.get_default_input_device_info() else None,
                "default_output": p.get_default_output_device_info()["index"] if p.get_default_output_device_info() else None
            }
        except Exception as e:
            print(f"Error checking audio devices: {e}")
            return {
                "input_devices": [],
                "output_devices": [],
                "default_input": None,
                "default_output": None,
                "error": str(e)
            }


def check_packages():
    """Check for required and optional packages."""
    packages = {
        "required": [
            "pyaudio",
            "numpy",
            "pyyaml",
            "speechrecognition"
        ],
        "optional": [
            "pyautogui",
            "keyboard",
            "pynput",
            "webrtcvad",
            "openai",
            "openai-whisper",
            "faster-whisper",
            "deepgram-sdk",
            "groq",
            "speechmatics"
        ]
    }
    
    results = {"required": {}, "optional": {}}
    
    for category, pkg_list in packages.items():
        for package in pkg_list:
            try:
                __import__(package.replace("-", "_"))
                results[category][package] = True
            except ImportError:
                results[category][package] = False
    
    return results


def launch_application(app_name: str):
    """Launch an application for testing."""
    try:
        if app_name == "terminal":
            # Open a new terminal window
            if platform.system() == "Linux":
                for terminal in ["gnome-terminal", "konsole", "xterm"]:
                    try:
                        subprocess.Popen([terminal, "--title", "Voice2Text Test"])
                        return True
                    except FileNotFoundError:
                        continue
                print("Could not find a terminal emulator")
                return False
        
        elif app_name == "gedit":
            subprocess.Popen(["gedit", "--new-document"])
            return True
        
        elif app_name == "firefox":
            subprocess.Popen(["firefox", "--new-window", "about:blank"])
            return True
        
        elif app_name == "chrome":
            subprocess.Popen(["google-chrome", "--new-window", "about:blank"])
            return True
        
        elif app_name == "word":
            if platform.system() == "Windows":
                subprocess.Popen(["start", "winword"])
                return True
            else:
                print("Microsoft Word is only available on Windows")
                return False
        
        else:
            # Try to launch the application directly
            subprocess.Popen([app_name])
            return True
            
    except Exception as e:
        print(f"Error launching {app_name}: {e}")
        return False


def test_text_output(app_name: str, text: str, delay: float = 5.0):
    """Test text output to an application."""
    print(f"Testing text output to {app_name}...")
    print(f"Waiting {delay} seconds for application to start...")
    time.sleep(delay)
    
    # Initialize text output
    text_output = TextOutput()
    
    # Type the text
    print(f"Typing: '{text}'")
    success = text_output.type_text(text)
    
    return {
        "application": app_name,
        "text": text,
        "success": success
    }


def record_and_recognize(duration: float, engine_name: str = None):
    """Record audio and recognize speech."""
    try:
        # Create audio input
        with ErrorSuppressor.suppress_stderr():
            audio_input = AudioInput()
        
        print(f"Recording audio for {duration} seconds...")
        
        # Record audio
        audio_data = audio_input.capture_audio(
            duration=duration,
            wait_for_speech=True
        )
        
        if not audio_data:
            print("Failed to record audio")
            return None
        
        print(f"Recorded {len(audio_data)} bytes of audio")
        
        # Get engine
        if engine_name:
            from core.engines import EngineRegistry
            engine = EngineRegistry.get_engine(engine_name)
        else:
            engine = EngineSelector.get_best_engine()
        
        if not engine:
            print("No speech recognition engine available")
            return None
        
        print(f"Recognizing with {engine.get_name()}...")
        
        # Recognize speech
        start_time = time.time()
        text = engine.recognize(audio_data)
        processing_time = time.time() - start_time
        
        if text:
            print(f"Recognized: '{text}'")
            print(f"Processing time: {processing_time:.2f}s")
            return text
        else:
            print("No speech recognized")
            return None
            
    except Exception as e:
        print(f"Error in record and recognize: {e}")
        return None


def main():
    """Main function."""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    print("==== Voice2Text Environment Test ====")
    
    # Check system info
    print("\n== System Information ==")
    system_info = check_system_info()
    for key, value in system_info.items():
        print(f"{key}: {value}")
    
    # Check audio devices
    print("\n== Audio Devices ==")
    audio_devices = check_audio_devices()
    
    if "error" in audio_devices:
        print(f"Error: {audio_devices['error']}")
    else:
        print("\nInput Devices:")
        for device in audio_devices["input_devices"]:
            print(f"  {device['index']}: {device['name']} - {int(device['channels'])} ch, {int(device['sample_rate'])} Hz" +
                  (" (default)" if device['index'] == audio_devices["default_input"] else ""))
        
        if not audio_devices["input_devices"]:
            print("  No input devices found")
    
    # Check packages
    print("\n== Package Availability ==")
    packages = check_packages()
    
    print("Required Packages:")
    for package, available in packages["required"].items():
        print(f"  {package}: {'✓' if available else '✗'}")
    
    print("\nOptional Packages:")
    for package, available in packages["optional"].items():
        print(f"  {package}: {'✓' if available else '-'}")
    
    # Test applications
    print("\n== Application Tests ==")
    
    # Get the text to use
    if args.record:
        recognized_text = record_and_recognize(args.duration, args.engine)
        test_text = recognized_text if recognized_text else args.test_phrase
    else:
        test_text = args.test_phrase
    
    # Test each application
    results = []
    for app in args.applications:
        print(f"\nTesting {app}...")
        if launch_application(app):
            result = test_text_output(app, test_text)
            results.append(result)
        else:
            print(f"Failed to launch {app}")
    
    # Summary
    print("\n== Test Summary ==")
    for result in results:
        status = "Success" if result["success"] else "Failed"
        print(f"{result['application']}: {status}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    with ErrorSuppressor.suppress_stderr():
        main()