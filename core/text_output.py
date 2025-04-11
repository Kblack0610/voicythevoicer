"""
Text Output Module for Voice2Text.

This module handles the output of recognized text to various targets,
primarily focusing on typing into the currently active application.
"""

import time
import logging
import threading
from typing import Optional, Dict, Any, Callable, List

logger = logging.getLogger("voice2text.output")


class TextOutput:
    """Handle text output operations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize text output system.
        
        Args:
            config: Dictionary containing output configuration
        """
        self.config = config or {}
        self.input_driver = None
        self.callbacks = []
        
        # Default settings
        self.delay_before_typing = self.config.get('pre_type_delay', 0.1)
        self.final_action = self.config.get('final_action', None)
        self.capitalize_sentences = self.config.get('capitalize_sentences', True)
        self.auto_punctuate = self.config.get('auto_punctuate', False)
        
        # Try to import pyautogui for typing
        self._import_pyautogui()
        
        # Set up notification handler
        self.notification_handler = self.config.get('notification_handler', self._default_notification)
    
    def _import_pyautogui(self):
        """Import PyAutoGUI for typing or fallback to alternative."""
        try:
            import pyautogui
            self.input_driver = pyautogui
            # Disable failsafe for smoother operation
            self.input_driver.FAILSAFE = False
            logger.info("Using PyAutoGUI for text output")
        except ImportError:
            logger.warning("PyAutoGUI not found, checking alternatives")
            self._try_alternative_drivers()
    
    def _try_alternative_drivers(self):
        """Try alternative input drivers if PyAutoGUI is not available."""
        # Try keyboard module
        try:
            import keyboard
            self.input_driver = keyboard
            logger.info("Using keyboard module for text output")
            return
        except ImportError:
            pass
        
        # Try pynput module
        try:
            from pynput.keyboard import Controller
            keyboard_controller = Controller()
            
            # Create compatible adapter
            class PynputAdapter:
                def __init__(self, controller):
                    self.controller = controller
                
                def write(self, text):
                    self.controller.type(text)
                
                def press(self, key):
                    self.controller.press(key)
                    self.controller.release(key)
            
            self.input_driver = PynputAdapter(keyboard_controller)
            logger.info("Using pynput for text output")
            return
        except ImportError:
            pass
            
        logger.error("No suitable input driver found! Text input will not work.")
        print("ERROR: No suitable input driver found. Please install one of:")
        print("- PyAutoGUI:   pip install --user pyautogui")
        print("- keyboard:    pip install --user keyboard")
        print("- pynput:      pip install --user pynput")
    
    def register_callback(self, callback: Callable[[str], None]):
        """
        Register a callback for text output.
        
        Args:
            callback: Function called when text is output
        """
        self.callbacks.append(callback)
    
    def _default_notification(self, message: str):
        """
        Default notification handler.
        
        Args:
            message: Message to display
        """
        print(f"\n=== {message} ===")
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before typing.
        
        Args:
            text: Original text
            
        Returns:
            Processed text
        """
        if not text:
            return text
            
        # Trim whitespace
        text = text.strip()
        
        # Apply capitalization if enabled
        if self.capitalize_sentences:
            text = self._ensure_capitalization(text)
        
        # Apply auto-punctuation if enabled
        if self.auto_punctuate:
            text = self._add_punctuation(text)
            
        return text
    
    def _ensure_capitalization(self, text: str) -> str:
        """
        Ensure proper capitalization of text.
        
        Args:
            text: Original text
            
        Returns:
            Text with proper capitalization
        """
        if not text:
            return text
            
        # Capitalize first letter if it's lowercase
        if text[0].islower():
            text = text[0].upper() + text[1:]
            
        return text
    
    def _add_punctuation(self, text: str) -> str:
        """
        Add punctuation to text if missing.
        
        Args:
            text: Original text
            
        Returns:
            Text with added punctuation
        """
        if not text:
            return text
            
        # Add period if text doesn't end with punctuation
        if not text[-1] in '.!?;:,':
            text = text + '.'
            
        return text
    
    def type_text(self, text: str) -> bool:
        """
        Type text to the current active window.
        
        Args:
            text: Text to type
            
        Returns:
            bool: Success or failure
        """
        if not text or not self.input_driver:
            return False
        
        # Preprocess text
        text = self.preprocess_text(text)
        
        try:
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(text)
                except Exception as e:
                    logger.error(f"Error in output callback: {e}")
            
            # Minimal pause before typing
            if self.delay_before_typing > 0:
                time.sleep(self.delay_before_typing)
            
            # Type text
            self.input_driver.write(text)
            logger.info(f"Typed text: {text}")
            
            # Add final action if configured
            if self.final_action:
                self._handle_final_action()
            
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
    
    def _handle_final_action(self):
        """Handle final action after typing text."""
        try:
            if self.final_action == 'enter':
                self.input_driver.press('enter')
            elif self.final_action == 'space':
                self.input_driver.press('space')
            elif self.final_action == 'tab':
                self.input_driver.press('tab')
            elif isinstance(self.final_action, str):
                self.input_driver.press(self.final_action)
        except Exception as e:
            logger.error(f"Error performing final action: {e}")
    
    def show_notification(self, message: str):
        """
        Show notification to the user.
        
        Args:
            message: Message to display
        """
        try:
            if self.notification_handler:
                self.notification_handler(message)
        except Exception as e:
            logger.error(f"Error showing notification: {e}")


class ClipboardOutput(TextOutput):
    """Output text to clipboard instead of typing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize clipboard output.
        
        Args:
            config: Dictionary containing output configuration
        """
        super().__init__(config)
        self.clipboard_available = self._check_clipboard()
    
    def _check_clipboard(self) -> bool:
        """
        Check if clipboard access is available.
        
        Returns:
            True if clipboard is available, False otherwise
        """
        try:
            import pyperclip
            self.clipboard = pyperclip
            return True
        except ImportError:
            logger.warning("pyperclip not available for clipboard operations")
            try:
                # Fallback to pyautogui if available
                if self.input_driver.__module__ == 'pyautogui':
                    self.clipboard = self.input_driver
                    return True
            except:
                pass
            return False
    
    def type_text(self, text: str) -> bool:
        """
        Copy text to clipboard.
        
        Args:
            text: Text to copy
            
        Returns:
            bool: Success or failure
        """
        if not text or not self.clipboard_available:
            return False
            
        # Preprocess text
        text = self.preprocess_text(text)
        
        try:
            # Copy to clipboard
            self.clipboard.copy(text)
            logger.info(f"Copied to clipboard: {text}")
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(text)
                except Exception as e:
                    logger.error(f"Error in output callback: {e}")
            
            # Show notification
            self.show_notification("Text copied to clipboard!")
            
            return True
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            return False