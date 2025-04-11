"""
OpenAI Whisper Speech Recognition Engine.

This module implements the Whisper speech recognition engine for Voice2Text,
providing high-quality local or API-based speech recognition.
"""

import os
import sys
import time
import logging
import tempfile
import threading
from typing import Optional, Dict, Any, List, Union

# Add the parent directory to path to fix relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engines import SpeechEngine, register_engine
from core.error_handlers import ErrorSuppressor

logger = logging.getLogger("voice2text.engines.whisper")


@register_engine("whisper")
class WhisperEngine(SpeechEngine):
    """OpenAI Whisper integration for local transcription."""
    
    def __init__(self, **kwargs):
        """
        Initialize Whisper engine.
        
        Args:
            **kwargs: Configuration options including:
                model_name: Whisper model size (default: "tiny")
                language: Language code (default: "en")
                device: Device to use (default: "cpu")
                compute_type: Computation type for faster-whisper (default: "int8")
        """
        self.config = {
            'model_name': 'tiny',  # tiny, base, small, medium, large
            'language': 'en',
            'device': 'cpu',  # cpu, cuda
            'compute_type': 'int8',  # float32, float16, int8
            'local_model_dir': os.environ.get('WHISPER_MODEL_DIR', None),
            'use_faster_whisper': True,  # Try to use faster-whisper if available
            'sample_rate': 16000,
        }
        self.config.update(kwargs)
        
        # First try faster-whisper (if enabled)
        self.model = None
        self.engine_type = "standard"
        
        if self.config['use_faster_whisper']:
            try:
                from faster_whisper import WhisperModel
                
                model_path = self.config['local_model_dir']
                if model_path:
                    model_path = os.path.join(model_path, self.config['model_name'])
                else:
                    model_path = self.config['model_name']
                
                self.model = WhisperModel(
                    model_path,
                    device=self.config['device'],
                    compute_type=self.config['compute_type']
                )
                self.engine_type = "faster"
                logger.info(f"Faster Whisper engine initialized with model {self.config['model_name']}")
            except ImportError:
                logger.warning("Faster Whisper not available, falling back to standard whisper")
        
        # Fall back to standard whisper if faster-whisper isn't available
        if self.model is None:
            try:
                import whisper
                
                # Determine model path/name
                model_path = self.config['local_model_dir']
                if model_path:
                    model_path = os.path.join(model_path, self.config['model_name'])
                    self.model = whisper.load_model(model_path)
                else:
                    self.model = whisper.load_model(self.config['model_name'])
                
                self.engine_type = "standard"
                logger.info(f"Standard Whisper engine initialized with model {self.config['model_name']}")
            except ImportError as e:
                logger.error(f"Failed to import whisper: {e}")
                logger.error("Please install whisper or faster-whisper:")
                logger.error("pip install --user openai-whisper")
                logger.error("OR")
                logger.error("pip install --user faster-whisper")
                print("Please install whisper or faster-whisper:")
                print("pip install --user openai-whisper")
                print("OR")
                print("pip install --user faster-whisper")
                
    def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
        """
        Convert audio data to text using Whisper.
        
        Args:
            audio_data: Raw audio bytes to process
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Recognized text or None if no speech detected
        """
        if self.model is None:
            return None
            
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_data)
            
        try:
            # Merge config with kwargs
            params = self.config.copy()
            params.update(kwargs)
            
            start_time = time.time()
            
            if self.engine_type == "faster":
                # Use faster-whisper
                segments, info = self.model.transcribe(
                    temp_path,
                    language=params['language'],
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                result = ""
                for segment in segments:
                    result += segment.text + " "
            else:
                # Use standard whisper
                result = self.model.transcribe(
                    temp_path,
                    language=params['language'],
                    fp16=False
                )["text"]
            
            end_time = time.time()
            latency = end_time - start_time
            logger.debug(f"Whisper recognition latency: {latency:.2f}s")
            
            if not result or result.isspace():
                return None
                
            return result.strip()
        except Exception as e:
            logger.error(f"Whisper recognition error: {e}")
            return None
        finally:
            # Remove temporary file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    def get_name(self) -> str:
        """
        Get the name of the engine.
        
        Returns:
            Engine name
        """
        return f"Whisper {self.config['model_name']} (Local)"
    
    def get_language_codes(self) -> List[str]:
        """
        Get supported language codes.
        
        Returns:
            List of supported language codes
        """
        return [
            "en", "es", "fr", "de", "it", "pt", "nl", "ru", "zh", "ja",
            "ko", "ar", "hi", "tr", "pl", "uk", "th", "vi", "id", "fa"
        ]
    
    def get_latency_profile(self) -> Dict[str, Any]:
        """
        Get latency characteristics of the engine.
        
        Returns:
            Dictionary with latency metrics
        """
        # Latency depends on model size
        if self.config['model_name'] in ['tiny', 'base']:
            avg_latency = 0.5 if self.engine_type == "faster" else 1.0
        elif self.config['model_name'] in ['small']:
            avg_latency = 1.0 if self.engine_type == "faster" else 2.0
        else:
            avg_latency = 2.0 if self.engine_type == "faster" else 4.0
            
        return {
            'avg_latency': avg_latency,
            'startup_time': 1.0,  # Time to initialize in seconds
            'requires_network': False,  # Does not require internet
            'streaming_capable': False  # Cannot process audio in real-time
        }
    
    def supports_streaming(self) -> bool:
        """
        Check if the engine supports streaming recognition.
        
        Returns:
            False for local Whisper
        """
        return False


@register_engine("whisper-api")
class WhisperAPIEngine(SpeechEngine):
    """OpenAI Whisper API integration."""
    
    def __init__(self, **kwargs):
        """
        Initialize Whisper API engine.
        
        Args:
            **kwargs: Configuration options including:
                api_key: OpenAI API key
                model: Whisper API model (default: "whisper-1")
                language: Language code (default: "en")
                temperature: Sampling temperature (default: 0)
                prompt: Optional prompt for context
        """
        self.config = {
            'api_key': os.environ.get('OPENAI_API_KEY'),
            'model': 'whisper-1',
            'language': 'en',
            'temperature': 0,
            'prompt': None,
            'sample_rate': 16000,
        }
        self.config.update(kwargs)
        
        try:
            import openai
            self.openai = openai
            
            # Set API key
            if self.config['api_key']:
                openai.api_key = self.config['api_key']
                logger.info("Whisper API engine initialized")
            else:
                logger.warning("OpenAI API key not set")
                print("Please set OPENAI_API_KEY environment variable or provide api_key in config")
        except ImportError as e:
            logger.error(f"Failed to import openai: {e}")
            logger.error("Please install OpenAI with: pip install openai")
            print("Please install OpenAI with: pip install openai")
            self.openai = None
        
    def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
        """
        Convert audio data to text using Whisper API.
        
        Args:
            audio_data: Raw audio bytes to process
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Recognized text or None if no speech detected
        """
        if not self.openai or not self.config['api_key']:
            return None
            
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_data)
            
        try:
            # Merge config with kwargs
            params = self.config.copy()
            params.update(kwargs)
            
            start_time = time.time()
            
            with open(temp_path, "rb") as audio_file:
                # Call Whisper API
                response = self.openai.Audio.transcribe(
                    model=params['model'],
                    file=audio_file,
                    language=params['language'],
                    temperature=params['temperature'],
                    prompt=params['prompt']
                )
            
            end_time = time.time()
            latency = end_time - start_time
            logger.debug(f"Whisper API recognition latency: {latency:.2f}s")
            
            if 'text' in response:
                return response['text'].strip()
            else:
                return None
        except Exception as e:
            logger.error(f"Whisper API recognition error: {e}")
            return None
        finally:
            # Remove temporary file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    def get_name(self) -> str:
        """
        Get the name of the engine.
        
        Returns:
            Engine name
        """
        return "Whisper API"
    
    def get_language_codes(self) -> List[str]:
        """
        Get supported language codes.
        
        Returns:
            List of supported language codes
        """
        # Whisper API supports all languages that the local model does
        return [
            "en", "es", "fr", "de", "it", "pt", "nl", "ru", "zh", "ja",
            "ko", "ar", "hi", "tr", "pl", "uk", "th", "vi", "id", "fa"
        ]
    
    def get_latency_profile(self) -> Dict[str, Any]:
        """
        Get latency characteristics of the engine.
        
        Returns:
            Dictionary with latency metrics
        """
        return {
            'avg_latency': 1.5,  # Average latency in seconds
            'startup_time': 0.1,  # Time to initialize in seconds
            'requires_network': True,  # Requires internet connection
            'streaming_capable': False  # Cannot process audio in real-time
        }
    
    def supports_streaming(self) -> bool:
        """
        Check if the engine supports streaming recognition.
        
        Returns:
            False for Whisper API
        """
        return False