"""
Speech Engine Interface.

This module defines the abstract interface that all speech recognition engines must implement.
It provides a standardized way to interact with different speech recognition backends.
"""

import abc
from typing import Optional, Dict, Any, List, Union
import time


class SpeechEngine(abc.ABC):
    """Abstract base class for all speech recognition engines."""
    
    @abc.abstractmethod
    def recognize(self, audio_data: bytes, **kwargs) -> Optional[str]:
        """
        Convert audio data to text.
        
        Args:
            audio_data: Raw audio bytes to process
            **kwargs: Engine-specific parameters
            
        Returns:
            Recognized text or None if no speech detected
        """
        pass
    
    @abc.abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the engine.
        
        Returns:
            Engine name as a string
        """
        pass
    
    @abc.abstractmethod
    def get_language_codes(self) -> List[str]:
        """
        Get supported language codes.
        
        Returns:
            List of supported language codes (e.g., ["en-US", "fr-FR"])
        """
        pass
    
    @abc.abstractmethod
    def get_latency_profile(self) -> Dict[str, Any]:
        """
        Get latency characteristics of the engine.
        
        Returns:
            Dictionary with latency metrics:
            {
                "startup_time": float,  # seconds to initialize
                "processing_time": float,  # seconds per 1s of audio
                "streaming_capable": bool,  # supports streaming input
                "min_chunk_size": int,  # minimum audio chunk in ms
            }
        """
        pass
    
    def supports_streaming(self) -> bool:
        """
        Check if the engine supports streaming recognition.
        
        Returns:
            True if streaming is supported, False otherwise
        """
        return self.get_latency_profile().get("streaming_capable", False)
    
    def measure_latency(self, audio_data: bytes, repetitions: int = 3) -> float:
        """
        Measure actual recognition latency.
        
        Args:
            audio_data: Sample audio data to process
            repetitions: Number of times to repeat the measurement
            
        Returns:
            Average latency in seconds
        """
        latencies = []
        for _ in range(repetitions):
            start_time = time.time()
            self.recognize(audio_data)
            end_time = time.time()
            latencies.append(end_time - start_time)
        
        return sum(latencies) / len(latencies)


class EngineRegistry:
    """Registry of available speech recognition engines."""
    
    _engines: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, engine_class: type):
        """
        Register a speech engine class.
        
        Args:
            name: Unique name for the engine
            engine_class: Engine class (subclass of SpeechEngine)
        """
        if not issubclass(engine_class, SpeechEngine):
            raise TypeError(f"Engine must be a subclass of SpeechEngine, got {engine_class}")
        
        cls._engines[name] = engine_class
    
    @classmethod
    def get_engine(cls, name: str, config: Dict[str, Any] = None) -> Optional[SpeechEngine]:
        """
        Get an instance of a registered engine.
        
        Args:
            name: Engine name to retrieve
            config: Configuration for the engine
            
        Returns:
            Engine instance or None if not found
        """
        engine_class = cls._engines.get(name)
        if not engine_class:
            return None
        
        return engine_class(**(config or {}))
    
    @classmethod
    def list_engines(cls) -> List[str]:
        """
        List all registered engine names.
        
        Returns:
            List of engine names
        """
        return list(cls._engines.keys())


def register_engine(name: str):
    """
    Decorator to register an engine class.
    
    Args:
        name: Name to register the engine under
        
    Returns:
        Decorator function
    """
    def decorator(cls):
        EngineRegistry.register(name, cls)
        return cls
    return decorator