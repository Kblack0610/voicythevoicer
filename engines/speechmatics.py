"""
Speechmatics Speech Recognition Engine.

This module implements the Speechmatics API for high-accuracy speech recognition,
optimized for business and professional use cases.
"""

import os
import time
import logging
import tempfile
import json
from typing import Optional, Dict, Any, List

import sys
import os

# Add the parent directory to path to fix relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engines import SpeechEngine, register_engine
from core.error_handlers import ErrorSuppressor

logger = logging.getLogger("voice2text.engines.speechmatics")


@register_engine("speechmatics")
class SpeechmaticsEngine(SpeechEngine):
    """
    Speechmatics speech recognition engine.
    
    Speechmatics offers enterprise-grade speech recognition with support
    for multiple languages and domains.
    """
    
    # Available operating points
    OPERATING_POINTS = {
        "enhanced": {"description": "Highest accuracy model", "relative_speed": 1.0},
        "standard": {"description": "Balanced performance and accuracy", "relative_speed": 1.2},
    }
    
    def __init__(self, **kwargs):
        """
        Initialize Speechmatics engine.
        
        Args:
            **kwargs: Configuration including:
                api_key: Speechmatics API key
                language: Language code (e.g., 'en', 'fr')
                operating_point: Operating point (standard, enhanced)
                sample_rate: Audio sample rate in Hz
        """
        self.config = {
            'api_key': os.environ.get('SPEECHMATICS_API_KEY'),
            'language': 'en',
            'operating_point': 'enhanced',
            'sample_rate': 16000,
            'channels': 1,
            'format': 'raw',
            'punctuate': True,
            'diarization': False,  # Speaker diarization
        }
        self.config.update(kwargs)
        
        # Initialize client
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Speechmatics client."""
        try:
            # First check if API key is available
            if not self.config['api_key']:
                logger.error("Speechmatics API key not provided")
                print("Please set SPEECHMATICS_API_KEY environment variable or provide api_key in config")
                return
            
            # Import Speechmatics with error suppression
            with ErrorSuppressor.suppress_stderr():
                try:
                    import speechmatics
                    from speechmatics.models import ConnectionSettings
                    
                    # Create connection settings
                    self.connection_settings = ConnectionSettings(
                        url="https://asr.api.speechmatics.com/v2",
                        auth_token=self.config['api_key']
                    )
                    
                    # Use the speechmatics.client module
                    self.client = speechmatics
                    
                    logger.info("Initialized Speechmatics client")
                    
                except ImportError:
                    logger.error("Speechmatics SDK not installed")
                    print("Please install the Speechmatics SDK:")
                    print("pip install --user speechmatics")
        except Exception as e:
            logger.error(f"Error initializing Speechmatics client: {e}")
    
    def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
        """
        Convert audio data to text using Speechmatics.
        
        Args:
            audio_data: Raw audio data bytes
            **kwargs: Additional parameters:
                language: Override language setting
                operating_point: Override operating point setting
                
        Returns:
            Recognized text or None on error
        """
        if not audio_data or not self.client:
            return None
            
        # Update config with any call-specific overrides
        config = dict(self.config)
        config.update(kwargs)
        
        try:
            # Create a temporary file for the audio data
            with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            try:
                # Configure transcription settings
                from speechmatics.batch_client import BatchClient
                from speechmatics.models import BatchTranscriptionConfig
                
                transcription_config = BatchTranscriptionConfig(
                    language=config['language'],
                    operating_point=config['operating_point'],
                    output_locale=config['language'],
                    enable_entities=True,
                    diarization=config['diarization'],
                )
                
                # Additional settings for audio details
                additional_params = {
                    "type": "raw",  # PCM audio format
                    "encoding": "pcm_s16le",  # Signed 16-bit little-endian PCM
                    "sample_rate": config['sample_rate'],
                    "channels": config['channels'],
                }
                
                # Create client and submit job
                with open(temp_path, 'rb') as audio_file:
                    client = BatchClient(self.connection_settings)
                    
                    # Submit the job and get the job ID
                    job_id = client.submit_job(
                        audio=audio_file,
                        transcription_config=transcription_config,
                        **additional_params
                    )
                    
                    # Wait for the job to complete
                    logger.debug(f"Submitted Speechmatics job {job_id}, waiting for results...")
                    
                    # Poll for job completion (every 0.5 seconds)
                    status = None
                    while status != "done":
                        job = client.get_job(job_id)
                        status = job.status
                        
                        if status == "failed":
                            logger.error(f"Speechmatics job {job_id} failed")
                            return None
                        
                        time.sleep(0.5)
                    
                    # Get the transcript
                    transcript = client.get_transcript(job_id, format="json")
                    
                    # Parse the JSON transcript
                    result = json.loads(transcript)
                    
                    # Extract the text
                    text = ""
                    for item in result.get("results", []):
                        if item.get("type") == "word" or item.get("type") == "punctuation":
                            text += item.get("alternatives", [{}])[0].get("content", "")
                            
                            # Add space after words, but not after punctuation
                            if item.get("type") == "word":
                                text += " "
                    
                    text = text.strip()
                    logger.debug(f"Speechmatics recognized: {text}")
                    return text
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error in Speechmatics recognition: {e}")
            return None
    
    def get_name(self) -> str:
        """
        Get the name of the engine.
        
        Returns:
            Engine name
        """
        return f"Speechmatics ({self.config['operating_point']})"
    
    def get_language_codes(self) -> List[str]:
        """
        Get supported language codes.
        
        Returns:
            List of supported language codes
        """
        # Speechmatics supported languages:
        # https://docs.speechmatics.com/features/languages
        return [
            "en",  # Global English
            "en-US",  # US English
            "en-AU",  # Australian English
            "en-GB",  # British English
            "es",  # Spanish
            "fr",  # French
            "de",  # German
            "it",  # Italian
            "ja",  # Japanese
            "nl",  # Dutch
            "pt",  # Portuguese
            "ca",  # Catalan
            "cs",  # Czech
            "da",  # Danish
            "fi",  # Finnish
            "hi",  # Hindi
            "hu",  # Hungarian
            "ko",  # Korean
            "lt",  # Lithuanian
            "lv",  # Latvian
            "nb",  # Norwegian
            "pl",  # Polish
            "ro",  # Romanian
            "ru",  # Russian
            "sk",  # Slovak
            "sv",  # Swedish
            "tr",  # Turkish
            "uk",  # Ukrainian
            "zh",  # Chinese (Mandarin)
        ]
    
    def get_latency_profile(self) -> Dict[str, Any]:
        """
        Get latency characteristics of the engine.
        
        Returns:
            Dictionary with latency metrics
        """
        # Speechmatics performance characteristics
        operating_point = self.config['operating_point']
        relative_speed = self.OPERATING_POINTS.get(operating_point, {}).get('relative_speed', 1.0)
        
        return {
            "startup_time": 0.1,  # seconds to initialize
            "processing_time": 0.5 / relative_speed,  # seconds per 1s of audio (approximate)
            "streaming_capable": False,  # Batch API only
            "min_chunk_size": 0.5,  # minimum audio chunk in seconds
            "network_dependent": True,
            "latency_category": "medium",  # overall latency category
        }
    
    def supports_streaming(self) -> bool:
        """
        Check if the engine supports streaming recognition.
        
        Returns:
            False (Speechmatics batch API doesn't support streaming)
        """
        return False