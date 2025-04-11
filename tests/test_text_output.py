"""
Tests for the text output module.

This module contains tests for the text output functionality, which handles
how recognized speech is typed into applications.
"""

import unittest
import os
import time
import threading
from unittest.mock import MagicMock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.text_output import TextOutput


class TestTextOutput(unittest.TestCase):
    """Test cases for the text output functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.text_output = TextOutput()
    
    def test_initialization(self):
        """Test initialization of TextOutput."""
        self.assertIsNotNone(self.text_output)
        self.assertFalse(self.text_output.capitalize_sentences)  # Default should be False
        
        # Test with custom parameters
        custom_output = TextOutput(
            capitalize_sentences=True,
            auto_punctuate=True,
            output_method='pyautogui'
        )
        self.assertTrue(custom_output.capitalize_sentences)
        self.assertTrue(custom_output.auto_punctuate)
        self.assertEqual(custom_output.output_method, 'pyautogui')
    
    def test_preprocess_text(self):
        """Test text preprocessing."""
        # Test capitalization
        capitalizer = TextOutput(capitalize_sentences=True)
        self.assertEqual(
            capitalizer._preprocess_text("hello world. this is a test."),
            "Hello world. This is a test."
        )
        
        # Test without capitalization
        no_capitalizer = TextOutput(capitalize_sentences=False)
        self.assertEqual(
            no_capitalizer._preprocess_text("hello world. this is a test."),
            "hello world. this is a test."
        )
    
    def test_auto_punctuate(self):
        """Test auto-punctuation functionality."""
        punctuator = TextOutput(auto_punctuate=True)
        
        # Test adding periods to the end of sentences
        self.assertEqual(
            punctuator._auto_punctuate("hello world"),
            "hello world."
        )
        
        # Test preserving existing punctuation
        self.assertEqual(
            punctuator._auto_punctuate("hello world!"),
            "hello world!"
        )
        
        # Test handling questions
        self.assertEqual(
            punctuator._auto_punctuate("how are you"),
            "how are you?"  # Ideally would detect questions, but basic implementation might just add period
        )
    
    @patch('core.text_output.pyautogui')
    def test_type_with_pyautogui(self, mock_pyautogui):
        """Test typing with pyautogui."""
        # Set up mock
        mock_pyautogui.write = MagicMock()
        
        # Create text output with pyautogui
        text_output = TextOutput(output_method='pyautogui')
        
        # Type some text
        result = text_output.type_text("Hello world")
        
        # Verify write was called
        mock_pyautogui.write.assert_called_once_with("Hello world")
        self.assertTrue(result)
    
    @patch('core.text_output.keyboard')
    def test_type_with_keyboard(self, mock_keyboard):
        """Test typing with keyboard module."""
        # Set up mock
        mock_keyboard.write = MagicMock()
        
        # Create text output with keyboard
        text_output = TextOutput(output_method='keyboard')
        
        # Type some text
        result = text_output.type_text("Hello world")
        
        # Verify write was called
        mock_keyboard.write.assert_called_once_with("Hello world")
        self.assertTrue(result)
    
    @patch('core.text_output.keyboard', None)  # Simulate keyboard not available
    @patch('core.text_output.pyautogui', None)  # Simulate pyautogui not available
    def test_fallback_typing(self):
        """Test fallback typing when preferred methods are not available."""
        # This is a bit tricky to test directly, but we can check the logic
        # that attempts to find an available typing method
        with patch('core.text_output.importlib.util.find_spec', return_value=None):
            text_output = TextOutput()
            self.assertEqual(text_output.output_method, None)
    
    def test_final_actions(self):
        """Test final actions after typing."""
        # Test with enter as final action
        with patch('core.text_output.pyautogui') as mock_pyautogui:
            mock_pyautogui.write = MagicMock()
            mock_pyautogui.press = MagicMock()
            
            text_output = TextOutput(output_method='pyautogui', final_action='enter')
            text_output.type_text("Hello world")
            
            mock_pyautogui.press.assert_called_once_with('enter')
    
    @patch('core.text_output.threading.Timer')
    def test_notification(self, mock_timer):
        """Test notification functionality."""
        # Set up mock
        mock_timer_instance = MagicMock()
        mock_timer.return_value = mock_timer_instance
        
        # Create text output with notification timeout
        text_output = TextOutput(notification_timeout=1.0)
        
        # Should create a timer
        text_output._show_notification("Test message")
        
        # Verify timer was created and started
        mock_timer.assert_called_once()
        mock_timer_instance.start.assert_called_once()


if __name__ == '__main__':
    unittest.main()