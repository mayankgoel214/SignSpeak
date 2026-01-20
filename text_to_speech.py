"""
Text-to-speech module for converting recognized signs to speech
"""

import pyttsx3
import threading


class TextToSpeech:
    def __init__(self):
        """Initialize text-to-speech engine"""
        try:
            self.engine = pyttsx3.init()

            # Configure voice properties
            self.engine.setProperty('rate', 150)  # Speed of speech
            self.engine.setProperty('volume', 0.9)  # Volume (0-1)

            # Get available voices
            voices = self.engine.getProperty('voices')
            if len(voices) > 0:
                self.engine.setProperty('voice', voices[0].id)  # Use first voice

            self.is_speaking = False

        except Exception as e:
            print(f"TTS initialization error: {e}")
            self.engine = None

    def speak(self, text):
        """
        Convert text to speech

        Args:
            text: Text to speak
        """
        if self.engine is None or not text:
            return

        # Run in separate thread to avoid blocking
        def _speak():
            try:
                self.is_speaking = True
                self.engine.say(text)
                self.engine.runAndWait()
                self.is_speaking = False
            except Exception as e:
                print(f"Speech error: {e}")
                self.is_speaking = False

        if not self.is_speaking:
            thread = threading.Thread(target=_speak)
            thread.daemon = True
            thread.start()

    def stop(self):
        """Stop current speech"""
        if self.engine is not None:
            try:
                self.engine.stop()
                self.is_speaking = False
            except Exception as e:
                print(f"Error stopping speech: {e}")

    def set_rate(self, rate):
        """
        Set speech rate

        Args:
            rate: Speech rate (words per minute)
        """
        if self.engine is not None:
            self.engine.setProperty('rate', rate)

    def set_volume(self, volume):
        """
        Set speech volume

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        if self.engine is not None:
            self.engine.setProperty('volume', max(0.0, min(1.0, volume)))
