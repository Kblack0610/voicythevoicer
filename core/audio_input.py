"""
Audio Input System for Voice2Text.

This module handles all audio capture operations with optimizations for
speech recognition and error suppression for ALSA/JACK audio systems.
"""

import os
import time
import logging
import threading
import numpy as np
import wave
from typing import Optional, Dict, Any, Tuple, List, Callable
from dataclasses import dataclass

from .error_handlers import ErrorSuppressor

logger = logging.getLogger("voice2text.audio")


@dataclass
class AudioConfig:
    """Configuration for audio input system."""
    
    # Basic audio parameters
    sample_rate: int = 16000  # Hz
    channels: int = 1  # Mono for speech recognition
    format: str = "int16"  # PCM 16-bit format
    chunk_size: int = 1024  # Samples per chunk
    
    # Speech detection parameters
    silence_threshold: float = 300  # Energy threshold for silence
    dynamic_silence: bool = True  # Adjust silence threshold dynamically
    min_speech_duration: float = 0.05  # Minimum speech to start recording
    speech_pad_start: float = 0.1  # Seconds of audio to include before speech
    speech_pad_end: float = 0.2  # Seconds of audio to include after speech ends
    
    # Hardware settings
    device_index: Optional[int] = None  # Input device index (None for default)
    timeout: float = 2.0  # Timeout for listening operations
    
    # Advanced settings
    vad_enabled: bool = True  # Use voice activity detection
    vad_mode: int = 1  # VAD aggressiveness (0-3)
    vad_frame_ms: int = 30  # VAD frame size in milliseconds


class VoiceActivityDetector:
    """
    Voice Activity Detector to identify speech in audio streams.
    
    This can use a simple energy-based VAD or a more sophisticated ML-based approach
    when available.
    """
    
    def __init__(self, config: AudioConfig):
        """
        Initialize VAD with configuration.
        
        Args:
            config: Audio configuration
        """
        self.config = config
        self._energy_threshold = config.silence_threshold
        self._dynamic_threshold = config.dynamic_silence
        self._vad = None
        
        # Try to load the webrtcvad module if available
        try:
            with ErrorSuppressor.suppress_stderr():
                import webrtcvad
                self._vad = webrtcvad.Vad(config.vad_mode)
                logger.info("Using WebRTC VAD for speech detection")
        except ImportError:
            logger.info("WebRTC VAD not available, using energy-based VAD")
    
    def is_speech(self, audio_frame: bytes, sample_rate: int = None) -> bool:
        """
        Check if audio frame contains speech.
        
        Args:
            audio_frame: Audio frame as bytes
            sample_rate: Sample rate for this frame (or use config default)
            
        Returns:
            True if speech detected, False otherwise
        """
        if sample_rate is None:
            sample_rate = self.config.sample_rate
            
        # Use WebRTC VAD if available
        if self._vad is not None:
            try:
                return self._vad.is_speech(audio_frame, sample_rate)
            except Exception as e:
                logger.debug(f"VAD error: {e}, falling back to energy detection")
        
        # Energy-based VAD as fallback
        return self._is_speech_energy(audio_frame)
    
    def _is_speech_energy(self, audio_frame: bytes) -> bool:
        """
        Detect speech using simple energy threshold.
        
        Args:
            audio_frame: Audio frame as bytes
            
        Returns:
            True if energy exceeds threshold
        """
        # Convert bytes to numpy array
        fmt = np.int16
        if self.config.format == 'float32':
            fmt = np.float32
            
        try:
            audio_array = np.frombuffer(audio_frame, dtype=fmt)
            energy = np.sqrt(np.mean(np.square(audio_array)))
            
            # Update threshold if using dynamic adjustment
            if self._dynamic_threshold:
                self._update_energy_threshold(energy)
                
            return energy > self._energy_threshold
        except Exception as e:
            logger.error(f"Error in energy calculation: {e}")
            return False
    
    def _update_energy_threshold(self, current_energy: float):
        """
        Dynamically adjust energy threshold based on ambient noise.
        
        Args:
            current_energy: Current frame energy
        """
        # Only update for non-speech frames (to track ambient noise)
        if current_energy < self._energy_threshold:
            # Slow adjustment toward ambient level (exponential moving average)
            self._energy_threshold = 0.95 * self._energy_threshold + 0.05 * (1.5 * current_energy)


class AudioInput:
    """Handle all audio input operations with error suppression."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize audio input system.
        
        Args:
            config: Dictionary containing audio configuration
        """
        # Convert dictionary config to AudioConfig
        if isinstance(config, dict):
            audio_args = {k: v for k, v in config.items() 
                         if k in AudioConfig.__annotations__}
            self.config = AudioConfig(**audio_args)
        else:
            self.config = config or AudioConfig()
        
        # Initialize VAD
        self.vad = VoiceActivityDetector(self.config)
        
        # Set up recording state
        self.is_recording = False
        self.stop_requested = False
        self.stream = None
        self.pyaudio = None
        
        # Set up audio buffer
        self.buffer = []
        self.buffer_lock = threading.Lock()
        
        # Import pyaudio with error suppression
        self._import_pyaudio()
    
    @ErrorSuppressor.suppress_alsa_errors
    def _import_pyaudio(self):
        """Import PyAudio with error suppression."""
        try:
            import pyaudio
            self.pyaudio = pyaudio
            logger.info("PyAudio imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import PyAudio: {e}")
            print("PyAudio not found. Please install: pip install --user pyaudio")
            print("On Linux, you may also need: sudo apt-get install portaudio19-dev")
            self.pyaudio = None
    
    @ErrorSuppressor.suppress_alsa_errors
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List available audio input devices.
        
        Returns:
            List of device information dictionaries
        """
        if not self.pyaudio:
            return []
            
        devices = []
        pa = self.pyaudio.PyAudio()
        
        try:
            for i in range(pa.get_device_count()):
                device_info = pa.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:  # Input device
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'sample_rate': int(device_info['defaultSampleRate'])
                    })
        finally:
            pa.terminate()
            
        return devices
    
    @ErrorSuppressor.suppress_alsa_errors
    def start_stream(self) -> bool:
        """
        Start audio stream with error handling.
        
        Returns:
            True if stream started successfully, False otherwise
        """
        if not self.pyaudio:
            return False
            
        if self.stream is not None:
            logger.warning("Stream already running, stopping first")
            self.stop_stream()
        
        try:
            pa = self.pyaudio.PyAudio()
            self.pa_instance = pa
            
            # Get format from config
            fmt = self.pyaudio.paInt16
            if self.config.format == 'float32':
                fmt = self.pyaudio.paFloat32
            
            # Create audio stream
            self.stream = pa.open(
                format=fmt,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.config.device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback if self.config.vad_enabled else None
            )
            
            self.is_recording = True
            self.stop_requested = False
            
            # Start stream
            self.stream.start_stream()
            logger.info("Audio stream started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting audio stream: {e}")
            if hasattr(self, 'pa_instance'):
                self.pa_instance.terminate()
            self.stream = None
            return False
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback for audio stream processing.
        
        This is called by PyAudio when new audio data is available.
        
        Args:
            in_data: Audio data as bytes
            frame_count: Number of frames
            time_info: Timing information
            status: Stream status
            
        Returns:
            Tuple of (None, flag) to continue streaming
        """
        if self.stop_requested:
            return None, self.pyaudio.paComplete
        
        # Check for speech
        is_speech = self.vad.is_speech(in_data)
        
        # Store audio data if recording or if speech detected
        if is_speech or self.is_recording:
            with self.buffer_lock:
                self.buffer.append(in_data)
        
        return None, self.pyaudio.paContinue
    
    @ErrorSuppressor.suppress_alsa_errors
    def capture_audio(self, duration: Optional[float] = None, 
                     wait_for_speech: bool = True) -> Optional[bytes]:
        """
        Capture audio with optional VAD.
        
        Args:
            duration: Maximum duration to capture in seconds
            wait_for_speech: Wait for speech to be detected before returning
            
        Returns:
            Audio data as bytes or None on error
        """
        if not self.stream:
            if not self.start_stream():
                return None
        
        # Clear buffer
        with self.buffer_lock:
            self.buffer = []
        
        # Calculate frames for duration
        max_frames = None
        if duration:
            bytes_per_second = self.config.sample_rate * self.config.channels * 2  # 16-bit
            max_frames = int(duration * bytes_per_second / self.config.chunk_size)
        
        # If using callback mode with VAD
        if self.config.vad_enabled:
            return self._capture_with_vad(max_frames, wait_for_speech)
        
        # Manual capture mode
        return self._capture_manual(max_frames, wait_for_speech)
    
    def _capture_with_vad(self, max_frames: Optional[int], 
                          wait_for_speech: bool) -> Optional[bytes]:
        """
        Capture audio using VAD in callback mode.
        
        Args:
            max_frames: Maximum frames to capture
            wait_for_speech: Wait for speech before returning
            
        Returns:
            Audio data as bytes
        """
        speech_detected = not wait_for_speech
        start_time = time.time()
        frames_captured = 0
        silence_frames = 0
        
        while True:
            # Check timeout
            if time.time() - start_time > self.config.timeout:
                logger.debug("Audio capture timeout")
                break
            
            # Check frame limit
            with self.buffer_lock:
                if max_frames and len(self.buffer) >= max_frames:
                    break
                
                # Check for speech in recent frames
                if not speech_detected and len(self.buffer) > 0:
                    # Check last frame for speech
                    if self.vad.is_speech(self.buffer[-1]):
                        speech_detected = True
                        logger.debug("Speech detected")
                
                # Check if enough silence after speech to stop capture
                if speech_detected:
                    # Count consecutive silent frames
                    if len(self.buffer) > 0 and not self.vad.is_speech(self.buffer[-1]):
                        silence_frames += 1
                    else:
                        silence_frames = 0
                    
                    # If enough silence, stop capturing
                    silence_secs = silence_frames * self.config.chunk_size / self.config.sample_rate
                    if silence_secs > self.config.speech_pad_end:
                        logger.debug(f"Silence detected after speech ({silence_secs:.2f}s)")
                        break
            
            # Sleep briefly to avoid busy waiting
            time.sleep(0.01)
        
        # Return captured audio
        with self.buffer_lock:
            if not self.buffer:
                return None
            return b''.join(self.buffer)
    
    def _capture_manual(self, max_frames: Optional[int], 
                        wait_for_speech: bool) -> Optional[bytes]:
        """
        Capture audio manually (without callback).
        
        Args:
            max_frames: Maximum frames to capture
            wait_for_speech: Wait for speech before returning
            
        Returns:
            Audio data as bytes
        """
        frames = []
        speech_detected = not wait_for_speech
        start_time = time.time()
        silence_frames = 0
        
        while True:
            # Check timeout
            if time.time() - start_time > self.config.timeout:
                logger.debug("Audio capture timeout")
                break
                
            # Read audio chunk
            try:
                data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                
                # Process chunk
                is_speech = self.vad.is_speech(data)
                
                if not speech_detected:
                    if is_speech:
                        speech_detected = True
                        logger.debug("Speech detected")
                        # Add previous segments to include speech_pad_start
                        frames.extend(frames[-int(self.config.speech_pad_start * 
                                              self.config.sample_rate / 
                                              self.config.chunk_size):])
                    
                if speech_detected:
                    frames.append(data)
                    
                    # Track silence for end detection
                    if not is_speech:
                        silence_frames += 1
                    else:
                        silence_frames = 0
                    
                    # If enough silence, stop capturing
                    silence_secs = silence_frames * self.config.chunk_size / self.config.sample_rate
                    if silence_secs > self.config.speech_pad_end:
                        logger.debug(f"Silence detected after speech ({silence_secs:.2f}s)")
                        break
                        
                # Check frame limit
                if max_frames and len(frames) >= max_frames:
                    break
                    
            except Exception as e:
                logger.error(f"Error reading audio: {e}")
                break
        
        if not frames:
            return None
        return b''.join(frames)
    
    @ErrorSuppressor.suppress_alsa_errors
    def stop_stream(self):
        """Stop and clean up audio stream."""
        self.stop_requested = True
        self.is_recording = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
            finally:
                self.stream = None
                
        if hasattr(self, 'pa_instance') and self.pa_instance:
            try:
                self.pa_instance.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")
            finally:
                self.pa_instance = None
                
        logger.info("Audio stream stopped")
    
    def save_audio(self, audio_data: bytes, filename: str) -> bool:
        """
        Save audio data to a WAV file.
        
        Args:
            audio_data: Audio data as bytes
            filename: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        if not audio_data:
            return False
            
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.config.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.config.sample_rate)
                wf.writeframes(audio_data)
            return True
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return False
    
    def __del__(self):
        """Clean up resources on deletion."""
        self.stop_stream()