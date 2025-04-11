#!/usr/bin/env python3
"""
Voice2Text - Modern voice-to-text tool with modular design.

This script is the main entry point for the Voice2Text application, which
converts speech to text and types it into the currently active application.
"""

import os
import sys
import time
import logging
import argparse
import threading
import yaml
from typing import Dict, Any, Optional

# Add parent directory to path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import core modules
from core.engines import EngineRegistry
from core.audio_input import AudioInput, AudioConfig
from core.text_output import TextOutput
from core.error_handlers import ErrorSuppressor

# Import all engines to ensure they're registered
try:
    from engines.google import GoogleEngine
except ImportError as e:
    logger.debug(f"Failed to import Google engine: {e}")

try:
    from engines.whisper import WhisperEngine
except ImportError as e:
    logger.debug(f"Failed to import Whisper engine: {e}")

try:
    from engines.deepgram import DeepgramEngine
except ImportError as e:
    logger.debug(f"Failed to import Deepgram engine: {e}")

try:
    from engines.groq import GroqEngine
except ImportError as e:
    logger.debug(f"Failed to import Groq engine: {e}")

try:
    from engines.speechmatics import SpeechmaticsEngine
except ImportError as e:
    logger.debug(f"Failed to import Speechmatics engine: {e}")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("voice2text")


class Voice2Text:
    """Main Voice2Text application class."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Voice2Text with configuration.
        
        Args:
            config: Configuration dictionary
        """
        # Default configuration
        self.default_config = {
            # Application settings
            'continuous': True,
            'debug': False,
            'quiet': True,
            
            # Engine settings
            'engine': 'google',
            'fallback_engine': None,
            'language_code': 'en-US',
            
            # Audio settings
            'audio': {
                'sample_rate': 16000,
                'channels': 1,
                'format': 'int16',
                'device_index': None,
                'vad_enabled': True,
                'silence_threshold': 400,
                'dynamic_silence': True,
            },
            
            # Output settings
            'output': {
                'pre_type_delay': 0.1,
                'final_action': None,
                'capitalize_sentences': True,
                'auto_punctuate': False,
            }
        }
        
        # Merge configurations
        self.config = self.default_config.copy()
        if config:
            self._deep_update(self.config, config)
        
        # Configure logging
        if self.config.get('debug', False):
            logging.getLogger('voice2text').setLevel(logging.DEBUG)
        
        # Suppress ALSA errors if quiet mode is enabled
        if self.config.get('quiet', True):
            ErrorSuppressor.redirect_stderr_to_file()
        
        # Initialize components
        self._init_components()
        
        # Application state
        self.is_running = False
    
    def _deep_update(self, d, u):
        """Recursively update a dictionary."""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
    
    def _init_components(self):
        """Initialize system components."""
        # Initialize audio input
        self.audio = AudioInput(self.config.get('audio', {}))
        
        # Initialize text output
        self.output = TextOutput(self.config.get('output', {}))
        
        # Get speech engine
        engine_name = self.config.get('engine', 'google')
        engine_config = {
            'language_code': self.config.get('language_code', 'en-US'),
            'sample_rate': self.config.get('audio', {}).get('sample_rate', 16000),
        }
        
        self.engine = EngineRegistry.get_engine(engine_name, engine_config)
        
        if not self.engine:
            logger.warning(f"Engine '{engine_name}' not found. Checking fallback.")
            
            # Try fallback engine
            fallback = self.config.get('fallback_engine')
            if fallback:
                self.engine = EngineRegistry.get_engine(fallback, engine_config)
                
            # Default to google if available
            if not self.engine and engine_name != 'google':
                logger.warning("Trying Google engine as last resort.")
                self.engine = EngineRegistry.get_engine('google', engine_config)
        
        if not self.engine:
            logger.error("No speech recognition engine available!")
            print("ERROR: No speech recognition engine available!")
            print("Please ensure at least one engine is properly installed.")
            sys.exit(1)
            
        logger.info(f"Using {self.engine.get_name()} for speech recognition")
    
    def start(self):
        """Start the Voice2Text system."""
        logger.info("Starting Voice2Text...")
        self.is_running = True
        
        try:
            # Show startup message
            self.output.show_notification(
                f"Voice2Text running with {self.engine.get_name()}.\n"
                "Speak to convert speech to text.\n"
                "Press Ctrl+C to exit."
            )
            
            # Start audio stream
            if not self.audio.start_stream():
                logger.error("Failed to start audio stream")
                return
            
            # Run in continuous mode or one-shot mode
            if self.config.get('continuous', True):
                self._run_continuous()
            else:
                self._run_single()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            print("\nVoice2Text stopped by user.")
        except Exception as e:
            logger.error(f"Error in Voice2Text: {e}")
        finally:
            self.stop()
    
    def _run_continuous(self):
        """Run in continuous mode."""
        logger.info("Running in continuous mode")
        
        while self.is_running:
            try:
                # Capture audio with speech detection
                audio_data = self.audio.capture_audio(wait_for_speech=True)
                
                if audio_data:
                    # Send to speech engine
                    text = self.engine.recognize(audio_data)
                    
                    if text:
                        # Type detected text
                        self.output.type_text(text)
                        # Give immediate feedback when text is processed
                        print(f"Recognized: {text}")
                    else:
                        logger.debug("No speech detected")
                        print("Listening... (No speech detected)")
                else:
                    print("Listening... (Awaiting speech)")
                
                # Short delay to prevent CPU spinning and allow Ctrl+C to work
                for _ in range(5):  # Check interrupt more frequently
                    if not self.is_running:
                        break
                    time.sleep(0.01)  # Shorter sleep intervals
            except KeyboardInterrupt:
                print("\nInterrupted by user. Exiting...")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Error in continuous mode: {e}")
                time.sleep(0.2)  # Longer delay after error
    
    def _run_single(self):
        """Run in single-shot mode."""
        logger.info("Running in single-shot mode")
        
        # Capture audio
        audio_data = self.audio.capture_audio(wait_for_speech=True)
        
        if audio_data:
            # Recognize speech
            text = self.engine.recognize(audio_data)
            
            if text:
                # Type recognized text
                self.output.type_text(text)
            else:
                logger.info("No speech detected")
        else:
            logger.info("No audio captured")
    
    def stop(self):
        """Stop the Voice2Text system."""
        self.is_running = False
        logger.info("Stopping Voice2Text...")
        
        if hasattr(self, 'audio'):
            self.audio.stop_stream()
            
        logger.info("Voice2Text stopped")


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file, or None for default
        
    Returns:
        Configuration dictionary
    """
    config = {}
    
    # Default config location
    if not config_path:
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'config.yaml'
        )
    
    # Load if file exists
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    else:
        logger.info(f"No configuration file found at {config_path}")
    
    return config or {}


def parse_args() -> Dict[str, Any]:
    """
    Parse command line arguments.
    
    Returns:
        Arguments as a dictionary
    """
    # Get available engines
    available_engines = EngineRegistry.list_engines()
    
    parser = argparse.ArgumentParser(
        description="Voice2Text - Convert speech to text with minimal latency",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Basic options
    parser.add_argument('--engine', '-e', choices=available_engines or ['google'], 
                      default='google', help='Speech recognition engine')
    parser.add_argument('--language', '-l', default='en-US',
                      help='Language code (e.g., en-US, fr-FR)')
    parser.add_argument('--no-continuous', '-n', action='store_true',
                      help='Run once instead of continuous mode')
    parser.add_argument('--quiet', '-q', action='store_true',
                      help='Suppress all ALSA/JACK error messages')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Enable debug logging')
    parser.add_argument('--config', '-c', help='Path to config file')
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--enter', action='store_true',
                            help='Add Enter key press after text')
    output_group.add_argument('--space', action='store_true',
                            help='Add Space key press after text')
    output_group.add_argument('--no-capitalize', action='store_true',
                            help='Disable automatic capitalization')
    output_group.add_argument('--punctuate', action='store_true',
                            help='Add punctuation automatically')
    
    # Advanced options
    adv_group = parser.add_argument_group('Advanced Options')
    adv_group.add_argument('--list-devices', action='store_true',
                         help='List available audio input devices and exit')
    adv_group.add_argument('--device', type=int,
                         help='Audio input device index')
    adv_group.add_argument('--sample-rate', type=int, default=16000,
                         help='Audio sample rate in Hz')
    
    # Testing
    parser.add_argument('--test', action='store_true',
                      help='Run test suite instead of normal operation')
    
    args = parser.parse_args()
    
    # Convert to dictionary
    config = vars(args)
    
    # Restructure for nested configuration
    result = {
        'engine': config['engine'],
        'language_code': config['language'],
        'continuous': not config['no_continuous'],
        'debug': config['debug'],
        'quiet': config['quiet'],
        
        'audio': {
            'sample_rate': config['sample_rate'],
            'device_index': config['device'],
        },
        
        'output': {
            'capitalize_sentences': not config['no_capitalize'],
            'auto_punctuate': config['punctuate'],
        }
    }
    
    # Set final action
    if config['enter']:
        result['output']['final_action'] = 'enter'
    elif config['space']:
        result['output']['final_action'] = 'space'
    
    return result, config


def run_tests():
    """Run the test suite."""
    import unittest
    import tests
    
    # Find test directory and load tests
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    suite = unittest.defaultTestLoader.discover(test_dir)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def list_input_devices():
    """List available audio input devices."""
    # Create temporary audio input instance
    audio = AudioInput()
    devices = audio.list_devices()
    
    if not devices:
        print("No audio input devices found")
        return
    
    print("\nAvailable Audio Input Devices:")
    print("-------------------------------")
    for device in devices:
        print(f"Device {device['index']}: {device['name']}")
        print(f"  Channels: {device['channels']}")
        print(f"  Sample Rate: {device['sample_rate']} Hz")
        print()
    
    print("To use a specific device, run with: --device DEVICE_INDEX")


def main():
    """Main entry point function."""
    # Parse command line arguments
    arg_config, raw_args = parse_args()
    
    # Run tests if requested
    if raw_args['test']:
        run_tests()
        return
    
    # List devices if requested
    if raw_args['list_devices']:
        list_input_devices()
        return
    
    # Load configuration from file
    file_config = load_config(raw_args['config'])
    
    # Merge configurations (command line args take precedence)
    config = file_config.copy()
    
    # Deep update with argument config
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                deep_update(d[k], v)
            else:
                d[k] = v
    
    deep_update(config, arg_config)
    
    # Create and start Voice2Text
    v2t = Voice2Text(config)
    v2t.start()


if __name__ == "__main__":
    main()