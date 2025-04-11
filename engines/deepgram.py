"""
Deepgram Speech Recognition Engine.

This module implements the Deepgram API for high-performance speech recognition,
offering extremely low latency and high accuracy.
"""

import os
import time
import logging
import tempfile
from typing import Optional, Dict, Any, List

import sys
import os

# Add the parent directory to path to fix relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engines import SpeechEngine, register_engine
from core.error_handlers import ErrorSuppressor

logger = logging.getLogger("voice2text.engines.deepgram")


@register_engine("deepgram")
class DeepgramEngine(SpeechEngine):
    """
    Deepgram speech recognition engine.
    
    Deepgram offers very low latency and high accuracy speech recognition,
    making it ideal for real-time voice-to-text applications.
    """
    
    # Available models
    MODELS = {
        "nova-2": {"description": "Most accurate general-purpose model", "relative_speed": 1.0},
        "nova": {"description": "Previous generation Nova", "relative_speed": 0.9},
        "enhanced": {"description": "Balanced performance and accuracy", "relative_speed": 1.2},
        "base": {"description": "Fastest, less accurate model", "relative_speed": 1.5}
    }
    
    def __init__(self, **kwargs):
        """
        Initialize Deepgram engine.
        
        Args:
            **kwargs: Configuration including:
                api_key: Deepgram API key
                model: Model to use (nova-2, nova, enhanced, base)
                language: Language code (e.g., 'en', 'fr')
                tier: Service tier (enhanced, base)
                keywords: List of keywords to boost recognition of
                sample_rate: Audio sample rate in Hz
        """
        self.config = {
            'api_key': os.environ.get('DEEPGRAM_API_KEY'),
            'model': 'nova-2',
            'language': 'en',
            'tier': 'enhanced',
            'keywords': [],
            'sample_rate': 16000,
            'channels': 1,
            'punctuate': True,
            'profanity_filter': False,
        }
        self.config.update(kwargs)
        
        # Initialize client
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Deepgram client."""
        try:
            # First check if API key is available
            if not self.config['api_key']:
                logger.error("Deepgram API key not provided")
                print("Please set DEEPGRAM_API_KEY environment variable or provide api_key in config")
                return
            
            # Import Deepgram with error suppression
            with ErrorSuppressor.suppress_stderr():
                try:
                    # Try new SDK first
                    from deepgram import (
                        DeepgramClient, 
                        PrerecordedOptions,
                        FileSource
                    )
                    
                    # Create client with SDK v2
                    self.client = DeepgramClient(self.config['api_key'])
                    self.sdk_version = 2
                    logger.info("Initialized Deepgram client (SDK v2)")
                    
                except ImportError:
                    # Try older SDK
                    try:
                        from deepgram import Deepgram
                        
                        # Create client with SDK v1
                        self.client = Deepgram(self.config['api_key'])
                        self.sdk_version = 1
                        logger.info("Initialized Deepgram client (SDK v1)")
                        
                    except ImportError:
                        logger.error("Deepgram SDK not installed")
                        print("Please install the Deepgram SDK:")
                        print("pip install --user deepgram-sdk")
        except Exception as e:
            logger.error(f"Error initializing Deepgram client: {e}")
    
    def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
        """
        Convert audio data to text using Deepgram.
        
        Args:
            audio_data: Raw audio data bytes
            **kwargs: Additional parameters:
                language: Override language setting
                model: Override model setting
                
        Returns:
            Recognized text or None on error
        """
        if not audio_data or not self.client:
            return None
            
        # Update config with any call-specific overrides
        config = dict(self.config)
        config.update(kwargs)
        
        try:
            # Need to ensure we have the right audio format
            if self.sdk_version == 2:
                return self._recognize_v2(audio_data, config)
            else:
                return self._recognize_v1(audio_data, config)
                
        except Exception as e:
            logger.error(f"Error in Deepgram recognition: {e}")
            return None
    
    def _recognize_v1(self, audio_data: bytes, config: Dict[str, Any]) -> Optional[str]:
        """Process with Deepgram SDK v1."""
        try:
            # Configure options
            options = {
                'punctuate': config['punctuate'],
                'model': config['model'],
                'language': config['language'],
                'tier': config['tier']
            }
            
            # Add keywords if specified
            if config['keywords']:
                options['keywords'] = config['keywords']
            
            # Add profanity filter if enabled
            if config['profanity_filter']:
                options['profanity_filter'] = True
            
            # Process with Deepgram API
            source = {'buffer': audio_data, 'mimetype': 'audio/raw'}
            response = self.client.transcription.sync_prerecorded(source, options)
            
            # Extract text from response
            if response and 'results' in response:
                text = response['results']['channels'][0]['alternatives'][0].get('transcript', '')
                logger.debug(f"Deepgram recognized: {text}")
                return text.strip()
            else:
                logger.warning("Empty or unexpected response from Deepgram")
                return None
                
        except Exception as e:
            logger.error(f"Error in Deepgram v1 recognition: {e}")
            return None
    
    def _recognize_v2(self, audio_data: bytes, config: Dict[str, Any]) -> Optional[str]:
        """Process with Deepgram SDK v2."""
        try:
            from deepgram import (
                PrerecordedOptions,
                FileSource,
                AudioEncoding
            )
            
            # Configure options
            options = PrerecordedOptions(
                model=config['model'],
                language=config['language'],
                smart_format=config['punctuate'],
                tier=config['tier'],
                encoding=AudioEncoding.Linear16,
                sample_rate=config['sample_rate'],
                channels=config['channels'],
            )
            
            # Add keywords if specified
            if config['keywords']:
                options.keywords = config['keywords']
            
            # Add profanity filter if enabled
            if config['profanity_filter']:
                options.profanity_filter = True
            
            # Save to temporary file (needed for SDK v2)
            with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            try:
                # Create file source
                source = FileSource(path=temp_path)
                
                # Process with Deepgram API
                response = self.client.listen.prerecorded.v("1").transcribe_file(source, options)
                
                # Extract text from response
                if response and hasattr(response, 'results'):
                    text = response.results.channels[0].alternatives[0].transcript
                    logger.debug(f"Deepgram recognized: {text}")
                    return text.strip()
                else:
                    logger.warning("Empty or unexpected response from Deepgram")
                    return None
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error in Deepgram v2 recognition: {e}")
            return None
    
    def get_name(self) -> str:
        """
        Get the name of the engine.
        
        Returns:
            Engine name
        """
        return f"Deepgram {self.config['model']}"
    
    def get_language_codes(self) -> List[str]:
        """
        Get supported language codes.
        
        Returns:
            List of supported language codes
        """
        # Deepgram supported languages:
        # https://developers.deepgram.com/documentation/features/language/
        return [
            "en",  # English
            "en-US",  # English (American)
            "en-GB",  # English (British)
            "en-AU",  # English (Australian)
            "en-IN",  # English (Indian)
            "en-NZ",  # English (New Zealand)
            "da",  # Danish
            "de",  # German
            "es",  # Spanish
            "es-419",  # Spanish (Latin American)
            "fr",  # French
            "hi",  # Hindi
            "hi-Latin",  # Hindi (Latin script)
            "it",  # Italian
            "ja",  # Japanese
            "ko",  # Korean
            "nl",  # Dutch
            "pl",  # Polish
            "pt",  # Portuguese
            "pt-BR",  # Portuguese (Brazilian)
            "ru",  # Russian
            "sv",  # Swedish
            "tr",  # Turkish
            "uk",  # Ukrainian
            "zh-CN",  # Chinese (Simplified)
        ]
    
    def get_latency_profile(self) -> Dict[str, Any]:
        """
        Get latency characteristics of the engine.
        
        Returns:
            Dictionary with latency metrics
        """
        # Deepgram is optimized for very low latency
        model = self.config['model']
        relative_speed = self.MODELS.get(model, {}).get('relative_speed', 1.0)
        
        return {
            "startup_time": 0.1,  # seconds to initialize
            "processing_time": 0.2 / relative_speed,  # seconds per 1s of audio (approximate)
            "streaming_capable": True,
            "min_chunk_size": 0.1,  # minimum audio chunk in seconds
            "network_dependent": True,
            "latency_category": "very_low",  # overall latency category
        }
    
    def supports_streaming(self) -> bool:
        """
        Check if the engine supports streaming recognition.
        
        Returns:
            True (Deepgram supports streaming)
        """
        return True