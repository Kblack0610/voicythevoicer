"""
Engine Selection Utilities.

This module provides utilities for automatic engine selection and fallback
based on availability, performance, and user preferences.
"""

import logging
import importlib.util
from typing import Optional, List, Dict, Any

from .engines import SpeechEngine, EngineRegistry

logger = logging.getLogger("voice2text.engine_selector")


class EngineSelector:
    """
    Utility for selecting the appropriate speech recognition engine.
    
    This class helps determine the best available engine based on various factors:
    - User preference
    - Availability of required packages
    - API key availability
    - Network connectivity
    - Performance requirements
    """
    
    # Performance categories for different use cases
    PERFORMANCE_CATEGORIES = {
        "offline": ["whisper"],
        "low_latency": ["deepgram", "groq", "google"],
        "high_accuracy": ["whisper", "speechmatics", "deepgram"],
        "multilingual": ["whisper", "google", "deepgram"],
    }
    
    @staticmethod
    def get_best_engine(
        preferred: Optional[str] = None,
        fallback: Optional[str] = None,
        category: Optional[str] = None,
        test_api_keys: bool = True
    ) -> SpeechEngine:
        """
        Get the best available speech recognition engine.
        
        Args:
            preferred: Preferred engine name
            fallback: Fallback engine name
            category: Performance category (offline, low_latency, high_accuracy, multilingual)
            test_api_keys: Whether to test if API keys are available
            
        Returns:
            Instance of the selected SpeechEngine or None if no suitable engine found
        """
        # Start with the list of all available engines
        available_engines = EngineRegistry.list_engines()
        
        if not available_engines:
            logger.error("No speech recognition engines available")
            return None
        
        # Check if preferred engine is available
        if preferred and preferred in available_engines:
            # Try to get the preferred engine
            engine = EngineSelector._try_get_engine(preferred, test_api_keys)
            if engine:
                logger.info(f"Using preferred engine: {engine.get_name()}")
                return engine
            else:
                logger.warning(f"Preferred engine '{preferred}' could not be initialized")
        
        # Check if fallback engine is specified and available
        if fallback and fallback in available_engines:
            engine = EngineSelector._try_get_engine(fallback, test_api_keys)
            if engine:
                logger.info(f"Using fallback engine: {engine.get_name()}")
                return engine
            else:
                logger.warning(f"Fallback engine '{fallback}' could not be initialized")
        
        # If a performance category is specified, try engines in that category
        if category and category in EngineSelector.PERFORMANCE_CATEGORIES:
            category_engines = EngineSelector.PERFORMANCE_CATEGORIES[category]
            
            for engine_name in category_engines:
                if engine_name in available_engines:
                    engine = EngineSelector._try_get_engine(engine_name, test_api_keys)
                    if engine:
                        logger.info(f"Using {category} category engine: {engine.get_name()}")
                        return engine
        
        # If we get here, try any available engine
        for engine_name in available_engines:
            engine = EngineSelector._try_get_engine(engine_name, test_api_keys)
            if engine:
                logger.info(f"Using available engine: {engine.get_name()}")
                return engine
        
        logger.error("No suitable speech recognition engine found")
        return None
    
    @staticmethod
    def _try_get_engine(engine_name: str, test_api_keys: bool) -> Optional[SpeechEngine]:
        """
        Try to initialize an engine and verify it's working.
        
        Args:
            engine_name: Name of the engine to initialize
            test_api_keys: Whether to test if API keys are available
            
        Returns:
            Initialized engine or None if initialization failed
        """
        try:
            engine = EngineRegistry.get_engine(engine_name)
            
            # For API-based engines, check if API key is available
            if test_api_keys and engine_name in ['google', 'deepgram', 'speechmatics', 'groq']:
                # This is a simple check - engines may have more sophisticated checks
                if not hasattr(engine, 'client') or not engine.client:
                    logger.warning(f"Engine '{engine_name}' initialized but API client is not available")
                    return None
            
            return engine
        except Exception as e:
            logger.warning(f"Failed to initialize engine '{engine_name}': {e}")
            return None
    
    @staticmethod
    def get_engine_comparison() -> Dict[str, Dict[str, Any]]:
        """
        Get a comparison of all available engines.
        
        Returns:
            Dictionary with engine comparisons
        """
        comparison = {}
        
        for engine_name in EngineRegistry.list_engines():
            try:
                engine = EngineRegistry.get_engine(engine_name)
                latency = engine.get_latency_profile()
                
                comparison[engine_name] = {
                    "name": engine.get_name(),
                    "latency_category": latency.get("latency_category", "unknown"),
                    "processing_time": latency.get("processing_time", 0),
                    "streaming_capable": latency.get("streaming_capable", False),
                    "network_dependent": latency.get("network_dependent", True),
                    "languages": len(engine.get_language_codes()),
                    "available": True
                }
            except Exception:
                comparison[engine_name] = {
                    "name": engine_name,
                    "available": False
                }
        
        return comparison