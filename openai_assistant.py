"""
OpenAI Assistant Module for SignSpeak AI
Provides enhanced functionality using GPT-4 and OpenAI APIs
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
import threading
import json
from datetime import datetime

# Load environment variables
load_dotenv()

class OpenAIAssistant:
    """
    OpenAI-powered assistant for SignSpeak AI
    Provides context-aware enhancements, learning assistance, and intelligent features
    """

    def __init__(self):
        """Initialize OpenAI client"""
        # Force reload of environment variables
        load_dotenv(override=True)
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")

        self.client = OpenAI(api_key=api_key)
        self.conversation_history = []
        self.context_mode = "casual"  # casual, medical, legal, educational, emergency

    def set_context_mode(self, mode):
        """Set conversation context mode"""
        valid_modes = ["casual", "medical", "legal", "educational", "emergency"]
        if mode in valid_modes:
            self.context_mode = mode
            print(f"Context mode set to: {mode}")
        else:
            print(f"Invalid mode. Choose from: {valid_modes}")

    def enhance_gesture_translation(self, gesture_text, confidence):
        """
        Enhance gesture translation with context awareness

        Args:
            gesture_text: Raw gesture text from classifier
            confidence: Confidence score of the gesture

        Returns:
            Enhanced translation with context
        """
        try:
            prompt = f"""You are assisting a sign language translation app.
Context mode: {self.context_mode}
Detected gesture: "{gesture_text}" (confidence: {confidence:.2%})

Based on the context mode and recent conversation, provide:
1. A contextually appropriate interpretation
2. Alternative meanings if confidence is low
3. Suggested follow-up clarifications if needed

Keep response brief and natural. Format as JSON with keys: "interpretation", "alternatives", "clarification"
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using faster model for real-time responses
                messages=[
                    {"role": "system", "content": "You are a helpful sign language translation assistant focused on accurate, context-aware interpretations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )

            result = response.choices[0].message.content

            # Try to parse as JSON, fallback to raw text
            try:
                # Remove markdown code blocks if present
                content = result
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                parsed = json.loads(content)
                # Ensure interpretation is just the text, not the whole JSON
                if "interpretation" in parsed:
                    if isinstance(parsed["interpretation"], str):
                        return parsed
                return parsed
            except Exception as parse_error:
                # If JSON parsing fails, use the gesture text directly
                return {
                    "interpretation": gesture_text,
                    "alternatives": [],
                    "clarification": None
                }

        except Exception as e:
            print(f"Error in gesture enhancement: {e}")
            return {
                "interpretation": gesture_text,
                "alternatives": [],
                "clarification": None
            }

    def generate_conversation_summary(self, history):
        """
        Generate intelligent summary of conversation history

        Args:
            history: List of (gesture, timestamp, confidence) tuples

        Returns:
            Formatted conversation summary
        """
        try:
            if not history:
                return "No conversation history yet."

            conversation_text = "\n".join([
                f"{timestamp}: {gesture} (confidence: {confidence:.1%})"
                for gesture, timestamp, confidence in history
            ])

            prompt = f"""Summarize this sign language conversation:

{conversation_text}

Provide a brief, natural summary of what was communicated. If patterns emerge (e.g., medical emergency, casual greeting), note them.
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes sign language conversations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.5
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Unable to generate summary."

    def explain_gesture(self, gesture_name):
        """
        Provide detailed explanation of how to perform a gesture

        Args:
            gesture_name: Name of the gesture

        Returns:
            Detailed explanation with tips
        """
        try:
            prompt = f"""Explain how to perform the American Sign Language (ASL) sign for "{gesture_name}".

Provide:
1. Hand shape and position
2. Movement description
3. Tips for clarity
4. Common mistakes to avoid

Keep it concise and beginner-friendly (2-3 sentences max).
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an ASL instructor helping people learn sign language."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error explaining gesture: {e}")
            return f"Unable to provide explanation for {gesture_name}."

    def speech_to_sign_instructions(self, text):
        """
        Convert text to sign language instructions

        Args:
            text: Text to convert to sign language

        Returns:
            Step-by-step signing instructions
        """
        try:
            prompt = f"""Convert this text to American Sign Language (ASL) instructions:
"{text}"

Provide:
1. Sign sequence (ordered list of signs needed)
2. Facial expressions or non-manual markers
3. Grammar notes (ASL grammar differs from English)

Be concise and practical.
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert in American Sign Language translation and instruction."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error converting to sign instructions: {e}")
            return "Unable to convert to sign language instructions."

    def transcribe_audio(self, audio_file_path):
        """
        Transcribe audio to text using OpenAI Whisper

        Args:
            audio_file_path: Path to audio file

        Returns:
            Transcribed text
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            return transcript.text

        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def generate_practice_feedback(self, intended_gesture, detected_gesture, confidence):
        """
        Provide feedback for learning/practice mode

        Args:
            intended_gesture: What the user was trying to sign
            detected_gesture: What was detected
            confidence: Detection confidence

        Returns:
            Constructive feedback
        """
        try:
            if intended_gesture.lower() == detected_gesture.lower() and confidence > 0.8:
                feedback_type = "success"
            elif intended_gesture.lower() == detected_gesture.lower():
                feedback_type = "correct_but_unclear"
            else:
                feedback_type = "incorrect"

            prompt = f"""A user is practicing ASL signs.
Intended sign: {intended_gesture}
Detected sign: {detected_gesture}
Confidence: {confidence:.1%}

Provide brief, encouraging feedback (1-2 sentences):
- If correct and clear: praise and encourage
- If correct but unclear: suggest clarity improvements
- If incorrect: gently point out the difference and encourage practice
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an encouraging ASL tutor providing constructive feedback."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error generating feedback: {e}")
            return "Keep practicing!"

    def suggest_next_words(self, current_conversation):
        """
        Suggest likely next words/signs based on context

        Args:
            current_conversation: Recent conversation context

        Returns:
            List of suggested next signs
        """
        try:
            prompt = f"""Based on this sign language conversation context:
"{current_conversation}"

Context mode: {self.context_mode}

Suggest 3-5 likely next signs the user might want to use. Consider the context mode.
Return only the sign names as a comma-separated list.
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are predicting likely next words in a sign language conversation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.6
            )

            suggestions = response.choices[0].message.content.strip().split(',')
            return [s.strip() for s in suggestions]

        except Exception as e:
            print(f"Error suggesting next words: {e}")
            return []

    def detect_emergency(self, recent_gestures):
        """
        Detect potential emergency situations from gesture sequence

        Args:
            recent_gestures: List of recent gestures

        Returns:
            (is_emergency: bool, emergency_type: str, confidence: float)
        """
        try:
            gestures_text = ", ".join(recent_gestures)

            prompt = f"""Analyze this sequence of sign language gestures for potential emergencies:
{gestures_text}

Emergency signs to look for: "help", "emergency", "doctor", "medicine", "stop", "bad", "pain", etc.

Respond in JSON format:
{{
    "is_emergency": true/false,
    "emergency_type": "medical/safety/none",
    "confidence": 0.0-1.0,
    "recommended_action": "brief suggestion"
}}
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an emergency detection system for sign language communication."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.2
            )

            content = response.choices[0].message.content
            # Try to extract JSON from markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return (
                result.get("is_emergency", False),
                result.get("emergency_type", "none"),
                result.get("confidence", 0.0),
                result.get("recommended_action", "")
            )

        except Exception as e:
            print(f"Error detecting emergency: {e}")
            return (False, "none", 0.0, "")

# Singleton instance
_assistant_instance = None

def get_assistant():
    """Get or create OpenAI assistant instance"""
    global _assistant_instance
    if _assistant_instance is None:
        try:
            _assistant_instance = OpenAIAssistant()
        except Exception as e:
            print(f"Failed to initialize OpenAI assistant: {e}")
            return None
    return _assistant_instance
