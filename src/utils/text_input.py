#!/usr/bin/env python
"""
Text Input Utilities for WhisperKey
Handles typing text directly at cursor location
"""
import logging
import time

import keyboard
import pyperclip

logger = logging.getLogger("whisperkey.text_input")


class TextInputManager:
    """Manages text input methods for transcribed text."""

    def __init__(self, config: dict):
        self.config = config
        self.typing_delay = config.get('typing', {}).get('delay_ms', 10) / 1000.0  # Convert to seconds

    def type_text_at_cursor(self, text: str, use_clipboard_fallback: bool = True):
        """
        Type text directly at the current cursor location.
        
        Args:
            text: Text to type
            use_clipboard_fallback: If True, fall back to clipboard if direct typing fails
        """
        if not text.strip():
            return

        try:
            # Method 1: Direct keyboard typing
            if self._type_text_directly(text):
                logger.info("Text typed directly at cursor")
                return

            # Method 2: Clipboard fallback
            if use_clipboard_fallback:
                self._paste_from_clipboard(text)
                logger.info("Text pasted from clipboard")

        except Exception as e:
            logger.error(f"Error typing text: {e}")
            # Final fallback - just copy to clipboard
            pyperclip.copy(text)

    def _type_text_directly(self, text: str) -> bool:
        """
        Type text directly using keyboard simulation.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Small delay to ensure the target application is ready
            time.sleep(0.1)

            # Type character by character with small delays
            for char in text:
                if char == '\n':
                    keyboard.press_and_release('enter')
                elif char == '\t':
                    keyboard.press_and_release('tab')
                else:
                    keyboard.write(char)

                # Small delay between characters to prevent issues
                if self.typing_delay > 0:
                    time.sleep(self.typing_delay)

            return True

        except Exception as e:
            logger.error(f"Direct typing failed: {e}")
            return False

    @staticmethod
    def _paste_from_clipboard(text: str):
        """
        Paste text using clipboard method.
        
        Args:
            text: Text to paste
        """
        try:
            # Save current clipboard content
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except:
                pass

            # Copy new text to clipboard
            pyperclip.copy(text)

            # Small delay
            time.sleep(0.1)

            # Paste using Ctrl+V
            keyboard.press_and_release('ctrl+v')

            # Restore original clipboard after a delay
            def restore_clipboard():
                time.sleep(1.0)  # Wait for paste to complete
                try:
                    pyperclip.copy(original_clipboard)
                except:
                    pass

            # Restore clipboard in background
            import threading
            threading.Timer(1.0, restore_clipboard).start()

        except Exception as e:
            logger.error(f"Clipboard paste failed: {e}")
            raise

    def type_text_with_formatting(self, text: str, add_space_before: bool = False, add_space_after: bool = True):
        """
        Type text with optional formatting.
        
        Args:
            text: Text to type
            add_space_before: Add space before text
            add_space_after: Add space after text
        """
        formatted_text = ""

        if add_space_before:
            formatted_text += " "

        formatted_text += text

        if add_space_after:
            formatted_text += " "

        self.type_text_at_cursor(formatted_text)

    def simulate_backspace(self, count: int = 1):
        """Simulate backspace key presses."""
        try:
            for _ in range(count):
                keyboard.press_and_release('backspace')
                if self.typing_delay > 0:
                    time.sleep(self.typing_delay)
        except Exception as e:
            logger.error(f"Backspace simulation failed: {e}")

    def simulate_delete(self, count: int = 1):
        """Simulate delete key presses."""
        try:
            for _ in range(count):
                keyboard.press_and_release('delete')
                if self.typing_delay > 0:
                    time.sleep(self.typing_delay)
        except Exception as e:
            logger.error(f"Delete simulation failed: {e}")


class RealtimeTextTyper:
    """Handles real-time text typing for streaming transcription."""

    def __init__(self, text_input_manager: TextInputManager):
        self.text_input_manager = text_input_manager
        self.is_active = False
        self.current_position = 0
        self.typed_text = ""

    def start_typing_session(self):
        """Start a real-time typing session."""
        self.is_active = True
        self.current_position = 0
        self.typed_text = ""
        logger.info("Started real-time typing session")

    def stop_typing_session(self):
        """Stop the real-time typing session."""
        self.is_active = False
        logger.info("Stopped real-time typing session")

    def type_incremental_text(self, new_text: str):
        """
        Type new text incrementally.
        
        Args:
            new_text: New text to add and type
        """
        if not self.is_active:
            return

        try:
            # Add new text to our buffer
            self.typed_text += new_text

            # Type the new text
            self.text_input_manager.type_text_at_cursor(new_text, use_clipboard_fallback=False)

            logger.debug(f"Typed incremental text: '{new_text}'")

        except Exception as e:
            logger.error(f"Error typing incremental text: {e}")

    def replace_last_word(self, new_word: str):
        """
        Replace the last typed word with a new word.
        
        Args:
            new_word: New word to replace the last word
        """
        if not self.is_active:
            return

        try:
            # Find the last word
            words = self.typed_text.split()
            if not words:
                self.type_incremental_text(new_word)
                return

            last_word = words[-1]

            # Remove the last word by backspacing
            backspace_count = len(last_word)
            self.text_input_manager.simulate_backspace(backspace_count)

            # Type the new word
            self.text_input_manager.type_text_at_cursor(new_word, use_clipboard_fallback=False)

            # Update our buffer
            words[-1] = new_word
            self.typed_text = " ".join(words)

            logger.debug(f"Replaced last word with: '{new_word}'")

        except Exception as e:
            logger.error(f"Error replacing last word: {e}")
