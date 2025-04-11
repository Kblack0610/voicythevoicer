"""
Speech recognition engines for the Voice Assistant.
Provides interfaces to different speech recognition services.
"""
import os
import logging
import tempfile
import json
import requests
from abc import ABC, abstractmethod

import speech_recognition as sr

logger = logging.getLogger("voice_assistant.speech")

class SpeechEngine(ABC):
    """Base class for speech recognition engines."""
    
    @abstractmethod
    def recognize(self, timeout=5):
        """
        Recognize speech and convert to text.
        
        Args:
            timeout (int): Maximum time to listen for speech in seconds
            
        Returns:
            str: Recognized text or empty string if no speech detected
        """
        pass

class GoogleSpeechEngine(SpeechEngine):
    """Google Speech Recognition engine."""
    
    def __init__(self, api_key=None):
        """
        Initialize Google Speech engine.
        
        Args:
            api_key (str, optional): Google Cloud API key. If None, uses free service with limitations.
        """
        self.recognizer = sr.Recognizer()
        self.api_key = api_key
        logger.debug("Initialized Google Speech Engine")
    
    def recognize(self, timeout=5):
        """Recognize speech using Google Speech Recognition."""
        with sr.Microphone() as source:
            logger.info("Adjusting for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info(f"Listening (timeout: {timeout}s)...")
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout)
                logger.debug("Audio captured, recognizing...")
                
                if self.api_key:
                    text = self.recognizer.recognize_google_cloud(audio, credentials_json=self.api_key)
                else:
                    text = self.recognizer.recognize_google(audio)
                    
                return text
            except sr.WaitTimeoutError:
                logger.debug("No speech detected within timeout period")
                return ""
            except sr.UnknownValueError:
                logger.info("Google Speech Recognition could not understand audio")
                return ""
            except sr.RequestError as e:
                logger.error(f"Could not request results from Google Speech Recognition service: {e}")
                return ""

class SphinxSpeechEngine(SpeechEngine):
    """CMU Sphinx Speech Recognition engine (offline)."""
    
    def __init__(self):
        """Initialize Sphinx Speech engine."""
        self.recognizer = sr.Recognizer()
        logger.debug("Initialized Sphinx Speech Engine")
    
    def recognize(self, timeout=5):
        """Recognize speech using CMU Sphinx (offline)."""
        with sr.Microphone() as source:
            logger.info("Adjusting for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info(f"Listening (timeout: {timeout}s)...")
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout)
                logger.debug("Audio captured, recognizing...")
                
                text = self.recognizer.recognize_sphinx(audio)
                return text
            except sr.WaitTimeoutError:
                logger.debug("No speech detected within timeout period")
                return ""
            except sr.UnknownValueError:
                logger.info("Sphinx could not understand audio")
                return ""
            except sr.RequestError as e:
                logger.error(f"Sphinx error: {e}")
                return ""

class AzureSpeechEngine(SpeechEngine):
    """Microsoft Azure Speech Recognition engine."""
    
    def __init__(self, api_key=None, region=None):
        """
        Initialize Azure Speech engine.
        
        Args:
            api_key (str): Azure Speech API key
            region (str): Azure region (e.g., "westus")
        """
        self.recognizer = sr.Recognizer()
        self.api_key = api_key or os.getenv("AZURE_SPEECH_KEY")
        self.region = region or os.getenv("AZURE_SPEECH_REGION")
        
        if not self.api_key or not self.region:
            logger.warning("Azure Speech API key or region not provided")
        
        logger.debug("Initialized Azure Speech Engine")
    
    def recognize(self, timeout=5):
        """Recognize speech using Azure Speech Recognition."""
        if not self.api_key or not self.region:
            logger.error("Azure Speech API key or region not provided")
            return ""
            
        with sr.Microphone() as source:
            logger.info("Adjusting for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info(f"Listening (timeout: {timeout}s)...")
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout)
                logger.debug("Audio captured, recognizing...")
                
                text = self.recognizer.recognize_azure(audio, 
                                                      key=self.api_key,
                                                      location=self.region)
                return text
            except sr.WaitTimeoutError:
                logger.debug("No speech detected within timeout period")
                return ""
            except sr.UnknownValueError:
                logger.info("Azure Speech Recognition could not understand audio")
                return ""
            except sr.RequestError as e:
                logger.error(f"Could not request results from Azure Speech Recognition service: {e}")
                return ""

class VoskSpeechEngine(SpeechEngine):
    """Vosk Speech Recognition engine (offline)."""
    
    def __init__(self, model_path=None):
        """
        Initialize Vosk Speech engine.
        
        Args:
            model_path (str, optional): Path to Vosk model directory
        """
        try:
            from vosk import Model, KaldiRecognizer
            self.vosk_available = True
            
            self.recognizer = sr.Recognizer()
            self.model_path = model_path or os.path.expanduser("~/.vosk/models/vosk-model-small-en-us-0.15")
            
            if not os.path.exists(self.model_path):
                logger.warning(f"Vosk model not found at {self.model_path}. Please download it from https://alphacephei.com/vosk/models")
                self.vosk_available = False
            else:
                self.model = Model(self.model_path)
                logger.debug("Initialized Vosk Speech Engine")
        except ImportError:
            logger.warning("Vosk package not installed. Run 'pip install vosk' to use this engine.")
            self.vosk_available = False
    
    def recognize(self, timeout=5):
        """Recognize speech using Vosk (offline)."""
        if not self.vosk_available:
            logger.error("Vosk not available. Cannot recognize speech.")
            return ""
            
        with sr.Microphone() as source:
            logger.info("Adjusting for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info(f"Listening (timeout: {timeout}s)...")
            
            try:
                from vosk import KaldiRecognizer
                
                audio = self.recognizer.listen(source, timeout=timeout)
                logger.debug("Audio captured, recognizing...")
                
                # Convert audio to format Vosk understands
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
                    f.write(audio.get_wav_data())
                    f.flush()
                    
                    sample_rate = 16000
                    rec = KaldiRecognizer(self.model, sample_rate)
                    
                    with open(f.name, "rb") as wavfile:
                        data = wavfile.read()
                        if rec.AcceptWaveform(data):
                            result = json.loads(rec.Result())
                            return result.get("text", "")
                        else:
                            result = json.loads(rec.FinalResult())
                            return result.get("text", "")
            except sr.WaitTimeoutError:
                logger.debug("No speech detected within timeout period")
                return ""
            except Exception as e:
                logger.error(f"Vosk error: {e}")
                return ""

class SpeechNoteEngine(SpeechEngine):
    """SpeechNote API for speech recognition."""
    
    def __init__(self, api_key=None):
        """
        Initialize SpeechNote engine.
        
        Args:
            api_key (str, optional): SpeechNote API key
        """
        self.recognizer = sr.Recognizer()
        self.api_key = api_key or os.getenv("SPEECHNOTE_API_KEY")
        
        if not self.api_key:
            logger.warning("SpeechNote API key not provided")
        
        logger.debug("Initialized SpeechNote Engine")
    
    def recognize(self, timeout=5):
        """Recognize speech using SpeechNote API."""
        if not self.api_key:
            logger.error("SpeechNote API key not provided")
            return ""
            
        with sr.Microphone() as source:
            logger.info("Adjusting for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info(f"Listening (timeout: {timeout}s)...")
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout)
                logger.debug("Audio captured, recognizing...")
                
                # Convert audio to format SpeechNote understands
                audio_data = audio.get_wav_data()
                
                # SpeechNote API endpoint (this is a fictional example)
                url = "https://api.speechnote.co/v1/recognize"
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "audio/wav"
                }
                
                response = requests.post(url, headers=headers, data=audio_data)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("text", "")
                else:
                    logger.error(f"SpeechNote API error: {response.status_code} - {response.text}")
                    return ""
                    
            except sr.WaitTimeoutError:
                logger.debug("No speech detected within timeout period")
                return ""
            except Exception as e:
                logger.error(f"SpeechNote error: {e}")
                return ""

def get_speech_engine(engine_type):
    """
    Factory function to get the appropriate speech engine.
    
    Args:
        engine_type (str): Type of speech engine to use
        
    Returns:
        SpeechEngine: Appropriate speech engine instance
    """
    engines = {
        "google": GoogleSpeechEngine,
        "sphinx": SphinxSpeechEngine,
        "azure": AzureSpeechEngine,
        "vosk": VoskSpeechEngine,
        "speechnote": SpeechNoteEngine
    }
    
    if engine_type not in engines:
        logger.warning(f"Unknown engine type: {engine_type}. Using Google Speech Recognition.")
        engine_type = "google"
    
    return engines[engine_type]()