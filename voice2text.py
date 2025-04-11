#!/usr/bin/env python3
"""
Voice2Text - Modern voice-to-text tool with modular design.

Features:
- Completely suppresses ALSA/JACK errors
- Minimal latency with optimized detection parameters
- Modular architecture for easy extension
- Built-in testing framework
"""

import argparse
import sys
import os
import io
import time
import logging
import contextlib
import tempfile
import unittest
import threading
from typing import Optional, Dict, Any, List, Callable

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("voice2text")

# -----------------------------------------------------------------------------
# Error Suppression Module
# -----------------------------------------------------------------------------

class ErrorSuppressor:
    """Class to handle all forms of error suppression."""
    
    @staticmethod
    @contextlib.contextmanager
    def suppress_stderr():
        """Completely suppress stderr output."""
        original_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            yield
        finally:
            sys.stderr = original_stderr
    
    @staticmethod
    @contextlib.contextmanager
    def suppress_stdout():
        """Completely suppress stdout output."""
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            yield
        finally:
            sys.stdout = original_stdout
    
    @staticmethod
    def suppress_alsa_errors(func):
        """Decorator to suppress ALSA errors for a function."""
        def wrapper(*args, **kwargs):
            with ErrorSuppressor.suppress_stderr():
                return func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def redirect_stderr_to_file(filepath=None):
        """Redirect stderr to a file instead of suppressing it completely."""
        if filepath is None:
            filepath = os.path.join(tempfile.gettempdir(), "voice2text_errors.log")
        sys.stderr = open(filepath, 'w')
        return filepath

# -----------------------------------------------------------------------------
# Audio Input Module
# -----------------------------------------------------------------------------

class AudioInput:
    """Handle all audio input operations with error suppression."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize audio input system.
        
        Args:
            config: Dictionary containing audio configuration.
        """
        self.config = config
        self.recognizer = None
        self.microphone = None
        
        # Import audio libraries with error suppression
        with ErrorSuppressor.suppress_stderr():
            try:
                import speech_recognition as sr
                self.sr = sr
                self.recognizer = sr.Recognizer()
                self.configure_recognizer()
                logger.info("Speech recognition system initialized")
            except ImportError as e:
                logger.error(f"Failed to import speech_recognition: {e}")
                self.handle_import_error()
                sys.exit(1)
    
    def configure_recognizer(self):
        """Configure the speech recognizer with optimized parameters."""
        # Optimize for minimal latency
        self.recognizer.pause_threshold = self.config.get('pause_threshold', 0.5)  # Faster end-of-speech detection
        self.recognizer.phrase_threshold = self.config.get('phrase_threshold', 0.1)  # Faster speech detection
        self.recognizer.non_speaking_duration = self.config.get('non_speaking_duration', 0.3)  # Faster reset
        self.recognizer.operation_timeout = self.config.get('operation_timeout', 3)  # Shorter API timeout
        
        # Energy threshold configuration
        if self.config.get('dynamic_energy', True):
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.dynamic_energy_adjustment_ratio = self.config.get('energy_adjustment_ratio', 1.5)
        else:
            self.recognizer.dynamic_energy_threshold = False
            self.recognizer.energy_threshold = self.config.get('energy_threshold', 400)
    
    @ErrorSuppressor.suppress_alsa_errors
    def create_microphone(self):
        """Create and return a microphone instance with error suppression."""
        if not self.sr:
            return None
        
        device_index = self.config.get('device_index', None)
        return self.sr.Microphone(device_index=device_index)
    
    @ErrorSuppressor.suppress_alsa_errors
    def adjust_for_ambient_noise(self, source, duration=0.5):
        """Adjust microphone for ambient noise with error suppression."""
        self.recognizer.adjust_for_ambient_noise(source, duration=duration)
    
    @ErrorSuppressor.suppress_alsa_errors
    def listen(self, source):
        """Listen for audio input with error suppression."""
        timeout = self.config.get('timeout', 1.5)
        phrase_time_limit = self.config.get('phrase_time_limit', 10.0)
        
        return self.recognizer.listen(
            source, 
            timeout=timeout, 
            phrase_time_limit=phrase_time_limit
        )
    
    def recognize(self, audio):
        """Recognize speech from audio data."""
        engine = self.config.get('engine', 'google')
        
        try:
            if engine == 'google':
                return self.recognizer.recognize_google(audio)
            elif engine == 'sphinx':
                return self.recognizer.recognize_sphinx(audio)
            else:
                logger.warning(f"Unknown engine: {engine}. Defaulting to Google.")
                return self.recognizer.recognize_google(audio)
        except self.sr.UnknownValueError:
            logger.debug("Could not understand audio")
            return None
        except self.sr.RequestError as e:
            logger.error(f"API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return None
    
    def handle_import_error(self):
        """Handle import error for speech recognition library."""
        error_msg = """
        Required libraries not found. Please install:
        
        pip install --user SpeechRecognition pyaudio
        
        On Ubuntu/Debian, you may also need:
        sudo apt-get install portaudio19-dev python3-pyaudio
        
        On Arch Linux:
        sudo pacman -S portaudio python-pyaudio
        """
        print(error_msg)

# -----------------------------------------------------------------------------
# Text Output Module
# -----------------------------------------------------------------------------

class TextOutput:
    """Handle text output operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize text output system.
        
        Args:
            config: Dictionary containing output configuration.
        """
        self.config = config
        
        # Import text output libraries
        try:
            import pyautogui
            self.pyautogui = pyautogui
            # Disable failsafe for smoother operation
            self.pyautogui.FAILSAFE = False
            logger.info("Text output system initialized")
        except ImportError as e:
            logger.error(f"Failed to import pyautogui: {e}")
            self.pyautogui = None
            print("PyAutoGUI not found. Please install: pip install --user pyautogui")
            sys.exit(1)
    
    def type_text(self, text: str) -> bool:
        """
        Type text to the current active window.
        
        Args:
            text: Text to type
            
        Returns:
            bool: Success or failure
        """
        if not text or not self.pyautogui:
            return False
        
        try:
            # Minimal pause before typing
            if self.config.get('pre_type_delay', 0.1) > 0:
                time.sleep(self.config.get('pre_type_delay', 0.1))
            
            # Type text
            self.pyautogui.write(text)
            
            # Add final action if configured
            final_action = self.config.get('final_action', None)
            if final_action == 'enter':
                self.pyautogui.press('enter')
            elif final_action == 'space':
                self.pyautogui.press('space')
            
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
    
    def show_notification(self, message: str):
        """Show notification to the user."""
        try:
            print(f"\n=== {message} ===")
        except Exception:
            pass

# -----------------------------------------------------------------------------
# Voice2Text Core
# -----------------------------------------------------------------------------

class Voice2Text:
    """Main Voice2Text class with modular design."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Voice2Text with custom configuration.
        
        Args:
            config: Dictionary containing configuration options
        """
        # Default configuration with optimized values
        self.default_config = {
            # Audio input settings
            'engine': 'google',
            'timeout': 1.5,
            'phrase_threshold': 0.1,
            'pause_threshold': 0.5,
            'non_speaking_duration': 0.3,
            'operation_timeout': 3.0,
            'dynamic_energy': True,
            'energy_adjustment_ratio': 1.5,
            'energy_threshold': 400,
            
            # Text output settings
            'pre_type_delay': 0.1,
            'final_action': None,
            
            # Application settings
            'continuous': True,
            'debug': False,
            'quiet': True,
            'ambient_duration': 0.3,
        }
        
        # Merge default config with provided config
        self.config = {**self.default_config, **(config or {})}
        
        # Configure logging
        if self.config.get('debug'):
            logger.setLevel(logging.DEBUG)
        
        # Completely redirect stderr to suppress ALSA errors if quiet mode is enabled
        if self.config.get('quiet'):
            ErrorSuppressor.redirect_stderr_to_file()
        
        # Initialize modules
        self.audio = AudioInput(self.config)
        self.output = TextOutput(self.config)
        
        # Runtime state
        self.is_running = False
        self.first_run = True
        self.ambient_adjusted = False
    
    def listen_and_recognize(self) -> Optional[str]:
        """
        Listen for speech and convert to text.
        
        Returns:
            str: Recognized text or None
        """
        # Create microphone with error suppression
        mic = self.audio.create_microphone()
        if not mic:
            return None
        
        with mic as source:
            # Adjust for ambient noise (once in continuous mode)
            if not self.ambient_adjusted or not self.config.get('continuous'):
                logger.info("Adjusting for ambient noise...")
                self.audio.adjust_for_ambient_noise(
                    source, 
                    duration=self.config.get('ambient_duration', 0.3)
                )
                self.ambient_adjusted = True
            
            # First-run announcement
            if self.first_run:
                if self.config.get('continuous'):
                    self.output.show_notification("Voice2Text ready! Listening for speech...")
                else:
                    self.output.show_notification(f"Listening (timeout: {self.config.get('timeout')}s)...")
                self.first_run = False
            
            try:
                # Listen for speech
                audio = self.audio.listen(source)
                
                # Recognize speech
                text = self.audio.recognize(audio)
                
                if text:
                    logger.info(f"Recognized: {text}")
                    return text
                return None
            except Exception as e:
                logger.error(f"Error in listen_and_recognize: {e}")
                return None
    
    def process_once(self) -> bool:
        """
        Process a single speech-to-text conversion.
        
        Returns:
            bool: True if text was processed, False otherwise
        """
        try:
            # Listen and recognize
            text = self.listen_and_recognize()
            
            # Type recognized text
            if text:
                return self.output.type_text(text)
            return False
        except Exception as e:
            logger.error(f"Error in process_once: {e}")
            return False
    
    def start(self):
        """Start the Voice2Text system."""
        logger.info("Starting Voice2Text...")
        self.is_running = True
        
        try:
            # Continuous mode
            if self.config.get('continuous'):
                self.start_continuous()
            # One-shot mode
            else:
                self.process_once()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in Voice2Text: {e}")
        finally:
            self.stop()
    
    def start_continuous(self):
        """Run in continuous mode."""
        # Display startup message
        self.output.show_notification(
            "Voice2Text running in continuous mode.\n"
            "Speak to convert speech to text.\n"
            "Press Ctrl+C to exit."
        )
        
        # Main continuous loop
        while self.is_running:
            try:
                if self.process_once():
                    # Short delay after successful recognition to prevent duplicates
                    time.sleep(0.1)
                else:
                    # Minimal delay to prevent CPU spinning
                    time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in continuous mode: {e}")
                time.sleep(0.2)  # Longer delay after error
    
    def stop(self):
        """Stop the Voice2Text system."""
        self.is_running = False
        logger.info("Voice2Text stopped")

# -----------------------------------------------------------------------------
# Testing Module
# -----------------------------------------------------------------------------

class Voice2TextTests(unittest.TestCase):
    """Test suite for Voice2Text."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_config = {
            'engine': 'google',
            'timeout': 0.5,
            'continuous': False,
            'debug': True,
            'quiet': True,
        }
    
    def test_initialization(self):
        """Test initialization of Voice2Text."""
        v2t = Voice2Text(self.test_config)
        self.assertIsInstance(v2t, Voice2Text)
        self.assertIsInstance(v2t.audio, AudioInput)
        self.assertIsInstance(v2t.output, TextOutput)
    
    def test_error_suppression(self):
        """Test error suppression."""
        original_stderr = sys.stderr
        with ErrorSuppressor.suppress_stderr():
            sys.stderr.write("This should be suppressed")
        self.assertEqual(sys.stderr, original_stderr)
    
    def test_audio_input_config(self):
        """Test audio input configuration."""
        v2t = Voice2Text(self.test_config)
        self.assertEqual(v2t.audio.config['engine'], 'google')
        self.assertEqual(v2t.audio.config['timeout'], 0.5)
    
    def test_output_config(self):
        """Test text output configuration."""
        v2t = Voice2Text({
            'pre_type_delay': 0.2,
            'final_action': 'enter'
        })
        self.assertEqual(v2t.output.config['pre_type_delay'], 0.2)
        self.assertEqual(v2t.output.config['final_action'], 'enter')

def run_tests():
    """Run the test suite."""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# -----------------------------------------------------------------------------
# Command Line Interface
# -----------------------------------------------------------------------------

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Voice2Text - Convert speech to text with minimal latency",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Basic options
    parser.add_argument('--engine', '-e', choices=['google', 'sphinx'], 
                      default='google', help='Speech recognition engine')
    parser.add_argument('--no-continuous', '-n', action='store_true',
                      help='Run once instead of continuous mode')
    parser.add_argument('--quiet', '-q', action='store_true',
                      help='Suppress all ALSA/JACK error messages')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Enable debug logging')
    
    # Advanced audio options
    audio_group = parser.add_argument_group('Audio Detection Options')
    audio_group.add_argument('--timeout', '-t', type=float, default=1.5,
                           help='Timeout for speech detection in seconds')
    audio_group.add_argument('--phrase-threshold', '-p', type=float, default=0.1,
                           help='Seconds of speech before triggering recognition')
    audio_group.add_argument('--pause-threshold', '-P', type=float, default=0.5,
                           help='Seconds of silence to mark the end of a phrase')
    audio_group.add_argument('--fixed-energy', '-f', action='store_true',
                           help='Use fixed energy threshold instead of dynamic')
    audio_group.add_argument('--energy-threshold', '-E', type=int, default=400,
                           help='Energy level threshold (with --fixed-energy)')
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--enter', action='store_true',
                            help='Add Enter key press after text')
    output_group.add_argument('--space', action='store_true',
                            help='Add Space key press after text')
    
    # Testing
    parser.add_argument('--test', action='store_true',
                      help='Run test suite instead of normal operation')
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_arguments()
    
    # Run tests if requested
    if args.test:
        run_tests()
        return
    
    # Configure from command line args
    config = {
        'engine': args.engine,
        'timeout': args.timeout,
        'continuous': not args.no_continuous,
        'debug': args.debug,
        'quiet': args.quiet,
        'phrase_threshold': args.phrase_threshold,
        'pause_threshold': args.pause_threshold,
        'dynamic_energy': not args.fixed_energy,
        'energy_threshold': args.energy_threshold,
    }
    
    # Configure output options
    if args.enter:
        config['final_action'] = 'enter'
    elif args.space:
        config['final_action'] = 'space'
    
    # Create and start Voice2Text
    v2t = Voice2Text(config)
    v2t.start()

if __name__ == "__main__":
    main()