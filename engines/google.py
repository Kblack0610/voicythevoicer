"""
Google Speech Recognition Engine.

This module implements the Google Cloud Speech-to-Text API integration
for Voice2Text, providing high-quality speech recognition.
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Any, List

# Add the parent directory to path to fix relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engines import SpeechEngine, register_engine
from core.error_handlers import ErrorSuppressor

logger = logging.getLogger("voice2text.engines.google")


@register_engine("google")
class GoogleEngine(SpeechEngine):
    """Google Speech-to-Text API integration."""
    
    def __init__(self, **kwargs):
        """
        Initialize Google Speech engine.
        
        Args:
            **kwargs: Configuration options including:
                language_code: Language code (default: 'en-US')
                api_key: Google API key (optional)
                use_enhanced: Use enhanced model (default: False)
                profanity_filter: Filter profanity (default: False)
                timeout: API request timeout (default: 5s)
        """
        self.config = {
            'language_code': 'en-US',
            'api_key': os.environ.get('GOOGLE_SPEECH_API_KEY'),
            'use_enhanced': False,
            'profanity_filter': False,
            'timeout': 5.0,
            'sample_rate': 16000,
        }
        self.config.update(kwargs)
        
        # Import speech_recognition with error suppression
        self.sr = None
        with ErrorSuppressor.suppress_stderr():
            try:
                import speech_recognition as sr
                self.sr = sr
                self.recognizer = sr.Recognizer()
                logger.info("Successfully imported speech_recognition and created Recognizer")
                self._configure_recognizer()
                logger.info("Google Speech engine initialized")
            except ImportError as e:
                logger.error(f"Failed to import speech_recognition: {e}")
                logger.error("Please install SpeechRecognition with: pip install SpeechRecognition")
                print("ERROR: speech_recognition library required for Google engine")
                print("Install with: pip install --user SpeechRecognition")
                raise
    
    def _configure_recognizer(self):
        """Configure recognizer with optimal settings."""
        # Set energy threshold for VAD
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        # Set non-speaking duration threshold
        self.recognizer.pause_threshold = 0.8
        # Set operation timeout
        self.recognizer.operation_timeout = self.config['timeout']
        # Set phrase timeout
        self.recognizer.phrase_time_limit = 10.0
        
    def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
        """
        Convert audio data to text using Google Speech API.
        
        Args:
            audio_data: Raw audio bytes to process
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Recognized text or None if no speech detected
        """
        if not self.sr:
            logger.error("Speech recognition not initialized")
            return None
            
        # Create AudioData from raw bytes
        sr_audio = self.sr.AudioData(
            audio_data, 
            sample_rate=self.config['sample_rate'],
            sample_width=2  # 16-bit PCM
        )
        
        # Merge config with kwargs
        params = self.config.copy()
        params.update(kwargs)
        
        start_time = time.time()
        try:
            # Use Google Speech API
            text = self.recognizer.recognize_google(
                sr_audio,
                key=params['api_key'],
                language=params['language_code'],
                show_all=False
            )
            end_time = time.time()
            latency = end_time - start_time
            logger.debug(f"Google recognition latency: {latency:.2f}s")
            
            return text
        except self.sr.UnknownValueError:
            logger.debug("Google could not understand audio")
            return None
        except self.sr.RequestError as e:
            logger.error(f"Google speech API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Google speech recognition error: {e}")
            return None
    
    def get_name(self) -> str:
        """
        Get the name of the engine.
        
        Returns:
            Engine name
        """
        return "Google Speech-to-Text"
    
    def get_language_codes(self) -> List[str]:
        """
        Get supported language codes.
        
        Returns:
            List of supported language codes
        """
        return [
            "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", 
            "ja-JP", "ru-RU", "zh-CN", "ko-KR", "pt-BR"
        ]
    
    def get_latency_profile(self) -> Dict[str, Any]:
        """
        Get latency characteristics of the engine.
        
        Returns:
            Dictionary with latency metrics
        """
        return {
            'avg_latency': 1.2,  # Average latency in seconds
            'startup_time': 0.1,  # Time to initialize in seconds
            'requires_network': True,  # Requires internet connection
            'streaming_capable': False  # Can process audio in real-time
        }
    
    def supports_streaming(self) -> bool:
        """
        Check if the engine supports streaming recognition.
        
        Returns:
            False for basic Google API
        """
        return False


# Optional: Enhanced Google Cloud Speech-to-Text client
# Only available if google-cloud-speech package is installed
try:
    from google.cloud import speech
    from google.oauth2 import service_account
    
    @register_engine("google-cloud")
    class GoogleCloudEngine(GoogleEngine):
        """Google Cloud Speech-to-Text advanced API integration."""
        
        def __init__(self, **kwargs):
            """
            Initialize Google Cloud Speech engine with enhanced features.
            
            Args:
                **kwargs: Configuration options including:
                    language_code: Language code (default: 'en-US')
                    credentials_path: Path to credentials JSON file
                    use_enhanced: Use enhanced model (default: True)
                    model: Model to use (default: 'command_and_search')
            """
            super().__init__(**kwargs)
            
            self.cloud_config = {
                'model': 'command_and_search',
                'use_enhanced': True,
                'credentials_path': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'),
            }
            self.cloud_config.update(kwargs)
            
            # Initialize Cloud client
            try:
                if self.cloud_config['credentials_path']:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.cloud_config['credentials_path']
                
                self.client = speech.SpeechClient()
                logger.info("Google Cloud Speech client initialized")
                
                # Set flag to indicate we should use Cloud API instead of basic API
                self.use_cloud_api = True
            except Exception as e:
                logger.error(f"Failed to initialize Google Cloud Speech client: {e}")
                self.use_cloud_api = False
        
        def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
            """
            Convert audio data to text using Google Cloud Speech API.
            
            Args:
                audio_data: Raw audio data bytes to process
                **kwargs: Additional parameters to override defaults
                
            Returns:
                Recognized text or None if no speech detected
            """
            # If Cloud API failed to initialize, fall back to basic API
            if not hasattr(self, 'use_cloud_api') or not self.use_cloud_api:
                return super().recognize(audio_data, **kwargs)
            
            # Merge config with kwargs
            params = self.cloud_config.copy()
            params.update(kwargs)
            
            try:
                # Configure recognition
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=self.config['sample_rate'],
                    language_code=params['language_code'],
                    model=params['model'],
                    use_enhanced=params['use_enhanced'],
                    profanity_filter=self.config['profanity_filter']
                )
                
                # Create audio object
                audio = speech.RecognitionAudio(content=audio_data)
                
                # Recognize speech
                start_time = time.time()
                response = self.client.recognize(config=config, audio=audio)
                end_time = time.time()
                latency = end_time - start_time
                logger.debug(f"Google Cloud recognition latency: {latency:.2f}s")
                
                # Process results
                results = ""
                for result in response.results:
                    results += result.alternatives[0].transcript + " "
                
                if results:
                    return results.strip()
                else:
                    logger.debug("No speech detected in audio")
                    return None
                
            except Exception as e:
                logger.error(f"Google Cloud Speech API error: {e}")
                # Fall back to basic API
                return super().recognize(audio_data, **kwargs)
        
        def get_name(self) -> str:
            """
            Get the name of the engine.
            
            Returns:
                Engine name
            """
            return "Google Cloud Speech"
        
        def get_latency_profile(self) -> Dict[str, Any]:
            """
            Get latency characteristics of the engine.
            
            Returns:
                Dictionary with latency metrics
            """
            return {
                'avg_latency': 0.8,  # Average latency in seconds (faster than basic API)
                'startup_time': 0.2,  # Time to initialize in seconds
                'requires_network': True,  # Requires internet connection
                'streaming_capable': True  # Can process audio in real-time
            }
        
        def supports_streaming(self) -> bool:
            """
            Check if the engine supports streaming recognition.
            
            Returns:
                True for Cloud API
            """
            return True
            
except ImportError:
    # Google Cloud Speech API not available
    logger.debug("Google Cloud Speech API not available. Install with: pip install google-cloud-speech")