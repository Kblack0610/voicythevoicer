"""
Groq Speech Recognition Engine.

This module implements Groq integration for ultra-fast speech recognition using LLMs.
Groq provides high-speed inference for Whisper models.
"""

import os
import time
import logging
import tempfile
import json
from typing import Optional, Dict, Any, List
import base64

import sys
import os

# Add the parent directory to path to fix relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engines import SpeechEngine, register_engine
from core.error_handlers import ErrorSuppressor

logger = logging.getLogger("voice2text.engines.groq")


@register_engine("groq")
class GroqEngine(SpeechEngine):
    """
    Groq-based speech recognition engine.
    
    This engine uses Groq's infrastructure for high-performance inference
    with Whisper-based models.
    """
    
    # Available models
    MODELS = {
        "distil-whisper-large": {
            "description": "Distilled Whisper Large model, fast and accurate",
            "relative_speed": 1.0
        },
        "whisper-large-v3": {
            "description": "Full Whisper Large v3 model", 
            "relative_speed": 0.8
        }
    }
    
    def __init__(self, **kwargs):
        """
        Initialize Groq engine.
        
        Args:
            **kwargs: Configuration including:
                api_key: Groq API key
                model: Model to use (whisper-large-v3, distil-whisper-large)
                language: Language hint (e.g., 'en', 'fr')
                sample_rate: Audio sample rate in Hz
        """
        self.config = {
            'api_key': os.environ.get('GROQ_API_KEY'),
            'model': 'distil-whisper-large',
            'language': 'en',
            'sample_rate': 16000,
            'channels': 1,
            'format': 'int16',
            'prompt': None,  # Optional prompt to guide transcription
        }
        self.config.update(kwargs)
        
        # Initialize client
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Groq client."""
        try:
            # First check if API key is available
            if not self.config['api_key']:
                logger.error("Groq API key not provided")
                print("Please set GROQ_API_KEY environment variable or provide api_key in config")
                return
            
            # Import Groq with error suppression
            with ErrorSuppressor.suppress_stderr():
                try:
                    import groq
                    
                    # Create client
                    self.client = groq.Groq(api_key=self.config['api_key'])
                    logger.info(f"Initialized Groq client with model {self.config['model']}")
                    
                except ImportError:
                    logger.error("Groq Python package not installed")
                    print("Please install the Groq package:")
                    print("pip install --user groq")
        except Exception as e:
            logger.error(f"Error initializing Groq client: {e}")
    
    def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
        """
        Convert audio data to text using Groq.
        
        Args:
            audio_data: Raw audio data bytes
            **kwargs: Additional parameters:
                language: Override language setting
                model: Override model setting
                prompt: Custom prompt for transcription
                
        Returns:
            Recognized text or None on error
        """
        if not audio_data or not self.client:
            return None
            
        # Update config with any call-specific overrides
        config = dict(self.config)
        config.update(kwargs)
        
        try:
            # Encode audio data to base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Prepare the prompt
            system_prompt = "You are a speech-to-text transcription system. Provide only the transcribed text without any additional commentary."
            user_prompt = config.get('prompt') or f"Transcribe the following audio. Language: {config['language']}."
            
            # Call the Groq API using chat completions
            response = self.client.chat.completions.create(
                model=config['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:audio/wav;base64,{audio_b64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0  # Use deterministic output for transcription
            )
            
            # Extract the transcription
            if response and hasattr(response, 'choices') and len(response.choices) > 0:
                text = response.choices[0].message.content
                
                # Clean up the text (remove quotes and markdown formatting if present)
                text = text.strip().strip('`').strip('"').strip()
                if text.lower().startswith('transcript:'):
                    text = text[len('transcript:'):].strip()
                
                logger.debug(f"Groq recognized: {text}")
                return text
            else:
                logger.warning("Empty or unexpected response from Groq")
                return None
                
        except Exception as e:
            logger.error(f"Error in Groq recognition: {e}")
            return None
    
    def get_name(self) -> str:
        """
        Get the name of the engine.
        
        Returns:
            Engine name
        """
        return f"Groq {self.config['model']}"
    
    def get_language_codes(self) -> List[str]:
        """
        Get supported language codes.
        
        Returns:
            List of supported language codes
        """
        # Models are based on Whisper, so they support the same languages
        return [
            "en",  # English
            "zh",  # Chinese
            "de",  # German
            "es",  # Spanish
            "ru",  # Russian
            "ko",  # Korean
            "fr",  # French
            "ja",  # Japanese
            "pt",  # Portuguese
            "tr",  # Turkish
            "pl",  # Polish
            "ca",  # Catalan
            "nl",  # Dutch
            "ar",  # Arabic
            "sv",  # Swedish
            "it",  # Italian
            "id",  # Indonesian
            "hi",  # Hindi
            "fi",  # Finnish
            "vi",  # Vietnamese
            "he",  # Hebrew
            "uk",  # Ukrainian
            "el",  # Greek
            "ms",  # Malay
            "cs",  # Czech
            "ro",  # Romanian
            "da",  # Danish
            "hu",  # Hungarian
            "ta",  # Tamil
            "no",  # Norwegian
            "th",  # Thai
            "ur",  # Urdu
            "hr",  # Croatian
            "bg",  # Bulgarian
            "lt",  # Lithuanian
            # And many more
        ]
    
    def get_latency_profile(self) -> Dict[str, Any]:
        """
        Get latency characteristics of the engine.
        
        Returns:
            Dictionary with latency metrics
        """
        # Groq is optimized for extremely fast inference
        model = self.config['model']
        relative_speed = self.MODELS.get(model, {}).get('relative_speed', 1.0)
        
        return {
            "startup_time": 0.1,  # seconds to initialize
            "processing_time": 0.3 / relative_speed,  # seconds per 1s of audio (approximate)
            "streaming_capable": False,
            "min_chunk_size": 0.5,  # minimum audio chunk in seconds
            "network_dependent": True,
            "latency_category": "low",  # overall latency category
        }
    
    def supports_streaming(self) -> bool:
        """
        Check if the engine supports streaming recognition.
        
        Returns:
            False (Groq API doesn't support streaming for audio yet)
        """
        return False