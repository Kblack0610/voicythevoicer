"""
Error handling utilities for Voice2Text.

This module provides tools to handle and suppress various types of errors,
particularly focused on ALSA/JACK audio system errors that commonly occur
with speech recognition on Linux systems.
"""

import os
import sys
import io
import logging
import contextlib
import tempfile
from typing import Optional, Callable, Any

logger = logging.getLogger("voice2text.errors")


class ErrorSuppressor:
    """Class to handle all forms of error suppression."""
    
    @staticmethod
    @contextlib.contextmanager
    def suppress_stderr():
        """
        Temporarily redirect stderr to a null device.
        
        This is useful for suppressing ALSA/JACK errors during audio operations.
        """
        original_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            yield
        finally:
            sys.stderr = original_stderr
    
    @staticmethod
    @contextlib.contextmanager
    def suppress_stdout():
        """
        Temporarily redirect stdout to a null device.
        
        This is useful when importing libraries that print to stdout.
        """
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            yield
        finally:
            sys.stdout = original_stdout
    
    @staticmethod
    @contextlib.contextmanager
    def redirect_stderr_to_file(filepath: Optional[str] = None):
        """
        Redirect stderr to a file instead of suppressing it completely.
        
        Args:
            filepath: Path to log file or None to use a temporary file
            
        Yields:
            Path to the log file
        """
        if filepath is None:
            filepath = os.path.join(tempfile.gettempdir(), "voice2text_errors.log")
        
        original_stderr = sys.stderr
        sys.stderr = open(filepath, 'w')
        try:
            yield filepath
        finally:
            sys.stderr.close()
            sys.stderr = original_stderr
    
    @staticmethod
    def suppress_alsa_errors(func: Callable) -> Callable:
        """
        Decorator to suppress ALSA errors for a function.
        
        Args:
            func: Function to decorate
            
        Returns:
            Wrapped function with ALSA error suppression
        """
        def wrapper(*args, **kwargs):
            with ErrorSuppressor.suppress_stderr():
                return func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def capture_stderr(func: Callable) -> Callable:
        """
        Decorator to capture stderr output from a function call.
        
        Args:
            func: Function to decorate
            
        Returns:
            Tuple of (function result, captured stderr)
        """
        def wrapper(*args, **kwargs):
            stderr_capture = io.StringIO()
            original_stderr = sys.stderr
            sys.stderr = stderr_capture
            try:
                result = func(*args, **kwargs)
                return result, stderr_capture.getvalue()
            finally:
                sys.stderr = original_stderr
        return wrapper


def filter_alsa_jack_errors(error_text: str) -> str:
    """
    Filter out common ALSA/JACK errors from error text.
    
    Args:
        error_text: Original error text
        
    Returns:
        Filtered error text
    """
    # Common error patterns to filter
    patterns = [
        "ALSA lib", 
        "Cannot connect to server socket", 
        "jack server",
        "JackShmReadWritePtr",
        "pcm_",
        "snd_"
    ]
    
    # Filter out lines containing these patterns
    result_lines = []
    for line in error_text.splitlines():
        if not any(pattern in line for pattern in patterns):
            result_lines.append(line)
    
    return "\n".join(result_lines)


def silent_import(module_name: str) -> Any:
    """
    Import a module while suppressing any stderr output.
    
    Args:
        module_name: Name of module to import
        
    Returns:
        Imported module or None if import fails
    """
    with ErrorSuppressor.suppress_stderr():
        try:
            return __import__(module_name)
        except ImportError:
            logger.debug(f"Failed to import {module_name}")
            return None