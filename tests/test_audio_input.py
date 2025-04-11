"""
Tests for the audio input module.

This module contains tests for the audio input functionality, including
voice activity detection (VAD) and audio capture.
"""

import unittest
import os
import time
import wave
import numpy as np
from typing import Optional
import threading

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audio_input import AudioInput
from core.error_handlers import ErrorSuppressor


class TestAudioInput(unittest.TestCase):
    """Test cases for the audio input functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up for all tests - create test audio data."""
        # Create a directory for test data if it doesn't exist
        cls.test_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # Create a test wave file
        cls.test_wave_path = os.path.join(cls.test_dir, 'test_audio.wav')
        cls._create_test_audio_file(cls.test_wave_path)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Remove test files
        if os.path.exists(cls.test_wave_path):
            os.remove(cls.test_wave_path)
    
    @classmethod
    def _create_test_audio_file(cls, file_path: str):
        """Create a test audio file with some speech-like content."""
        # Parameters
        sample_rate = 16000
        duration = 2.0  # seconds
        frequency = 440  # A4 note
        
        # Generate time points
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Generate a tone that varies in amplitude (like speech)
        envelope = np.sin(2 * np.pi * 0.5 * t) * 0.5 + 0.5  # Amplitude envelope
        tone = np.sin(2 * np.pi * frequency * t) * envelope
        
        # Add some noise to simulate speech
        noise = np.random.normal(0, 0.01, tone.shape)
        signal = tone + noise
        
        # Scale to 16-bit range
        signal = np.int16(signal / np.max(np.abs(signal)) * 32767 * 0.9)
        
        # Save as WAV file
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(signal.tobytes())
    
    def test_audio_input_initialization(self):
        """Test basic initialization of AudioInput."""
        # Initialize with default settings
        with ErrorSuppressor.suppress_stderr():
            audio_input = AudioInput()
        
        self.assertIsNotNone(audio_input)
        self.assertEqual(audio_input.sample_rate, 16000)
        self.assertEqual(audio_input.channels, 1)
        self.assertEqual(audio_input.format, 'int16')
        
        # Test with custom settings
        with ErrorSuppressor.suppress_stderr():
            custom_audio = AudioInput(
                sample_rate=44100,
                channels=2,
                device_index=None,
                format='float32'
            )
        
        self.assertEqual(custom_audio.sample_rate, 44100)
        self.assertEqual(custom_audio.channels, 2)
        self.assertEqual(custom_audio.format, 'float32')
    
    def test_energy_vad(self):
        """Test energy-based voice activity detection."""
        with ErrorSuppressor.suppress_stderr():
            audio_input = AudioInput(vad_mode='energy')
        
        # Load test audio data
        with wave.open(self.test_wave_path, 'rb') as wf:
            audio_data = wf.readframes(wf.getnframes())
        
        # Convert to numpy array for processing
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Test for speech in the sample
        self.assertTrue(audio_input._detect_speech_energy(audio_array))
        
        # Test with silent data
        silent_data = np.zeros(16000, dtype=np.int16)  # 1 second of silence
        self.assertFalse(audio_input._detect_speech_energy(silent_data))
    
    @unittest.skip("Requires microphone hardware - use only when needed")
    def test_audio_capture(self):
        """Test audio capture functionality."""
        with ErrorSuppressor.suppress_stderr():
            audio_input = AudioInput()
        
        # Test short capture (non-blocking)
        audio_data = audio_input.capture_audio(duration=0.5, wait_for_speech=False)
        
        # Just verify we got some data
        self.assertIsNotNone(audio_data)
        self.assertGreater(len(audio_data), 0)
    
    def test_vad_setup(self):
        """Test setting up different VAD modes."""
        # Test energy-based VAD
        with ErrorSuppressor.suppress_stderr():
            energy_vad = AudioInput(vad_mode='energy')
        self.assertEqual(energy_vad.vad_mode, 'energy')
        
        # Test WebRTC VAD if available
        try:
            import webrtcvad
            with ErrorSuppressor.suppress_stderr():
                webrtc_vad = AudioInput(vad_mode='webrtc')
            self.assertEqual(webrtc_vad.vad_mode, 'webrtc')
        except ImportError:
            pass
        
        # Test disabled VAD
        with ErrorSuppressor.suppress_stderr():
            no_vad = AudioInput(vad_mode=None)
        self.assertIsNone(no_vad.vad_mode)
    
    def test_audio_format_conversion(self):
        """Test audio format conversion utilities."""
        with ErrorSuppressor.suppress_stderr():
            audio_input = AudioInput()
        
        # Create some test data in int16 format
        int16_data = np.ones(1000, dtype=np.int16) * 16000
        
        # Convert to float32
        float32_data = audio_input._convert_format(int16_data, 'int16', 'float32')
        self.assertEqual(float32_data.dtype, np.float32)
        self.assertLess(abs(float32_data[0] - 0.5), 0.01)  # Should be around 0.5
        
        # Convert back
        int16_back = audio_input._convert_format(float32_data, 'float32', 'int16')
        self.assertEqual(int16_back.dtype, np.int16)
        self.assertLess(abs(int16_back[0] - 16000), 100)  # Should be close to original


if __name__ == '__main__':
    unittest.main()