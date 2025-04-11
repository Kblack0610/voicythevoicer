"""
Tests for speech recognition engines.

This module contains tests for the various speech recognition engines and the engine registry.
"""

import unittest
import os
import wave
import numpy as np
from typing import Optional

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engines import SpeechEngine, EngineRegistry
from engines.google import GoogleEngine


class TestEngineRegistry(unittest.TestCase):
    """Test cases for the engine registry."""
    
    def test_engine_registration(self):
        """Test registering and retrieving engines."""
        # Google engine should be registered automatically
        self.assertIn('google', EngineRegistry.list_engines())
        
        # Get engine instance
        engine = EngineRegistry.get_engine('google')
        self.assertIsNotNone(engine)
        self.assertIsInstance(engine, GoogleEngine)


class TestGoogleEngine(unittest.TestCase):
    """Test cases for the Google speech recognition engine."""
    
    def setUp(self):
        """Set up for tests."""
        self.engine = GoogleEngine()
        self.test_audio = self._generate_test_audio()
    
    def _generate_test_audio(self) -> Optional[bytes]:
        """Generate test audio data for testing."""
        try:
            # Create a silent audio sample
            sample_rate = 16000
            duration = 1.0  # seconds
            
            # Generate silent audio (zeros)
            samples = np.zeros(int(sample_rate * duration), dtype=np.int16)
            
            # Add a simple tone to make it non-silent
            tone_freq = 440.0  # A4 note
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            samples += (np.sin(2 * np.pi * tone_freq * t) * 32767 * 0.3).astype(np.int16)
            
            # Convert to bytes
            return samples.tobytes()
        except Exception as e:
            print(f"Error generating test audio: {e}")
            return None
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.get_name(), "Google Speech-to-Text")
        
    def test_language_codes(self):
        """Test that language codes are available."""
        language_codes = self.engine.get_language_codes()
        self.assertIsNotNone(language_codes)
        self.assertIn("en-US", language_codes)
        
    def test_latency_profile(self):
        """Test that latency profile is correctly returned."""
        profile = self.engine.get_latency_profile()
        self.assertIsNotNone(profile)
        self.assertIn("processing_time", profile)
        self.assertIn("streaming_capable", profile)
        
    def test_recognize_empty_audio(self):
        """Test recognition with empty audio data."""
        result = self.engine.recognize(b'')
        self.assertIsNone(result)
    
    @unittest.skip("Skipping actual API call test - use only when needed")
    def test_recognize_with_audio(self):
        """Test recognition with actual audio."""
        if not self.test_audio:
            self.skipTest("Failed to generate test audio")
            
        # This will actually call the Google API if not skipped
        result = self.engine.recognize(self.test_audio)
        
        # We don't expect actual speech to be recognized in synthetic audio
        # but the function should run without error
        self.assertIsNone(result)


class TestEngineRegistration(unittest.TestCase):
    """Test creating and registering a custom engine."""
    
    def test_custom_engine_registration(self):
        """Test that custom engines can be registered."""
        # Create a mock engine class
        class MockEngine(SpeechEngine):
            def recognize(self, audio_data, **kwargs):
                return "mock result"
                
            def get_name(self):
                return "Mock Engine"
                
            def get_language_codes(self):
                return ["en-US"]
                
            def get_latency_profile(self):
                return {
                    "processing_time": 0.1,
                    "streaming_capable": False,
                    "min_chunk_size": 0.1
                }
        
        # Register the engine
        EngineRegistry.register("mock", MockEngine)
        
        # Check it was registered
        self.assertIn("mock", EngineRegistry.list_engines())
        
        # Get an instance
        engine = EngineRegistry.get_engine("mock")
        self.assertIsNotNone(engine)
        self.assertEqual(engine.get_name(), "Mock Engine")
        
        # Test recognition
        self.assertEqual(engine.recognize(b''), "mock result")


if __name__ == '__main__':
    unittest.main()