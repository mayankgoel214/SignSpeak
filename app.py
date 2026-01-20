"""
SignSpeak AI - Real-time Sign Language Translation
Main application with Gradio interface
"""

import gradio as gr
import cv2
import numpy as np
from hand_detector import HandLandmarkDetector
from gesture_classifier import GestureClassifier
from text_to_speech import TextToSpeech
from openai_assistant import get_assistant
import time


class SignSpeakApp:
    def __init__(self):
        """Initialize SignSpeak AI application"""
        self.hand_detector = HandLandmarkDetector(max_hands=1, detection_con=0.7)
        self.gesture_classifier = GestureClassifier()
        self.tts = TextToSpeech()
        self.ai_assistant = get_assistant()

        self.last_gesture = ""
        self.last_gesture_time = 0
        self.gesture_hold_time = 1.5  # Seconds to hold gesture before speaking
        self.conversation_history = []
        self.context_mode = "casual"  # casual, medical, legal, educational, emergency
        self.ai_enhancement_enabled = True
        self.emergency_detected = False

    def process_frame(self, frame):
        """
        Process video frame for sign language recognition

        Args:
            frame: Input video frame

        Returns:
            annotated_frame: Frame with annotations
            gesture_text: Recognized gesture text
            confidence: Detection confidence
        """
        if frame is None:
            return None, "No input", 0.0

        # Ensure frame is valid numpy array
        try:
            if not isinstance(frame, np.ndarray):
                return None, "Invalid frame", 0.0
            if len(frame.shape) != 3:
                return None, "Invalid frame dimensions", 0.0
        except Exception as e:
            print(f"Frame validation error: {e}")
            return None, "Frame error", 0.0

        # Detect hands
        hands, annotated_frame = self.hand_detector.detect_hands(frame)

        # Extract features
        features = self.hand_detector.extract_features(hands)

        # Classify gesture
        gesture_name, confidence = self.gesture_classifier.classify_gesture(features)

        # Add text overlay
        if features is not None:
            cv2.putText(
                annotated_frame,
                f"Gesture: {gesture_name}",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 0),
                2
            )
            cv2.putText(
                annotated_frame,
                f"Confidence: {confidence:.1%}",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )

            # Trigger speech if gesture held for threshold time
            current_time = time.time()
            if gesture_name == self.last_gesture:
                if current_time - self.last_gesture_time > self.gesture_hold_time:
                    if confidence > 0.6:  # Only speak if confident
                        # Use AI enhancement if available
                        spoken_text = gesture_name
                        enhanced_info = None

                        if self.ai_assistant and self.ai_enhancement_enabled:
                            try:
                                enhanced_info = self.ai_assistant.enhance_gesture_translation(
                                    gesture_name, confidence
                                )
                                if enhanced_info and "interpretation" in enhanced_info:
                                    interpretation = enhanced_info["interpretation"]
                                    # Use the gesture name if interpretation is too complex
                                    if isinstance(interpretation, str) and len(interpretation) < 100:
                                        spoken_text = interpretation
                                    else:
                                        spoken_text = gesture_name
                            except Exception as e:
                                print(f"AI enhancement error: {e}")
                                spoken_text = gesture_name

                        self.tts.speak(spoken_text)
                        self.conversation_history.append({
                            "time": time.strftime("%H:%M:%S"),
                            "gesture": gesture_name,
                            "confidence": confidence,
                            "enhanced": enhanced_info
                        })

                        # Check for emergency
                        self._check_emergency()

                        # Reset to avoid repeating
                        self.last_gesture_time = current_time + 2
            else:
                self.last_gesture = gesture_name
                self.last_gesture_time = current_time

        else:
            gesture_name = "No hand detected"
            confidence = 0.0
            self.last_gesture = ""

        return annotated_frame, gesture_name, confidence

    def text_to_sign(self, text):
        """
        Convert text to sign language with AI-powered instructions

        Args:
            text: Input text

        Returns:
            message: Sign language instructions
        """
        if not text:
            return "Please enter some text"

        # Speak the text
        self.tts.speak(text)

        # Get AI-powered sign language instructions
        if self.ai_assistant:
            try:
                sign_instructions = self.ai_assistant.speech_to_sign_instructions(text)
                return f"📝 Text: {text}\n\n🤟 Sign Language Instructions:\n{sign_instructions}\n\n💡 The text has been spoken aloud. Follow the instructions above to sign it in ASL."
            except Exception as e:
                print(f"AI text-to-sign error: {e}")

        # Fallback
        return f"Text '{text}' would be displayed as sign language animation.\n\nFor MVP, this feature shows the text and speaks it. Full sign animation will be implemented in future versions."

    def get_conversation_history(self):
        """Get formatted conversation history with AI summary"""
        if not self.conversation_history:
            return "No conversation yet"

        history = "Conversation History:\n" + "="*50 + "\n"
        for i, entry in enumerate(self.conversation_history[-10:], 1):  # Last 10 entries
            history += f"{i}. [{entry['time']}] {entry['gesture']} (confidence: {entry['confidence']:.1%})\n"

        # Add AI summary
        if self.ai_assistant and len(self.conversation_history) > 0:
            try:
                history_data = [
                    (entry['gesture'], entry['time'], entry['confidence'])
                    for entry in self.conversation_history[-10:]
                ]
                summary = self.ai_assistant.generate_conversation_summary(history_data)
                history += f"\n{'='*50}\n📊 AI Summary:\n{summary}\n"
            except Exception as e:
                print(f"AI summary error: {e}")

        return history

    def _check_emergency(self):
        """Check recent gestures for emergency situations"""
        if not self.ai_assistant or len(self.conversation_history) < 2:
            return

        try:
            recent_gestures = [entry['gesture'] for entry in self.conversation_history[-5:]]
            is_emergency, emergency_type, confidence, action = self.ai_assistant.detect_emergency(recent_gestures)

            if is_emergency and confidence > 0.7:
                # Only alert once every 10 gestures to avoid spam
                if not self.emergency_detected or len(self.conversation_history) % 10 == 0:
                    self.emergency_detected = True
                    alert_msg = f"⚠️ EMERGENCY DETECTED: {emergency_type.upper()} - {action}"
                    print(alert_msg)
                    # Don't speak emergency every time to avoid interrupting
            else:
                # Reset emergency flag if no emergency detected
                if len(self.conversation_history) % 5 == 0:
                    self.emergency_detected = False
        except Exception as e:
            print(f"Emergency check error: {e}")

    def set_context_mode(self, mode):
        """Set conversation context mode"""
        self.context_mode = mode
        if self.ai_assistant:
            self.ai_assistant.set_context_mode(mode)
        return f"Context mode set to: {mode}"

    def get_gesture_explanation(self, gesture_name):
        """Get detailed explanation of a gesture"""
        if not self.ai_assistant:
            return f"Explanation for {gesture_name} is not available without AI assistant."

        try:
            explanation = self.ai_assistant.explain_gesture(gesture_name)
            return f"🤟 How to sign '{gesture_name}':\n\n{explanation}"
        except Exception as e:
            print(f"Explanation error: {e}")
            return f"Unable to get explanation for {gesture_name}"

    def toggle_ai_enhancement(self, enabled):
        """Toggle AI enhancement on/off"""
        self.ai_enhancement_enabled = enabled
        status = "enabled" if enabled else "disabled"
        return f"AI enhancement {status}"


def create_interface():
    """Create Gradio interface for SignSpeak AI"""

    app = SignSpeakApp()

    with gr.Blocks(title="SignSpeak AI - Real-time Sign Language Translation") as interface:

        gr.Markdown(
            """
            # 🤟 SignSpeak AI
            ### Real-time Sign Language Translation powered by AI

            **Break communication barriers for 285 million deaf and hard-of-hearing people worldwide**

            ---
            """
        )

        with gr.Tabs():

            # Tab 1: Sign-to-Speech
            with gr.Tab("👋 Sign to Speech"):
                gr.Markdown(
                    """
                    ### How to use:
                    1. Allow camera access
                    2. Perform ASL gestures in front of the camera
                    3. Hold gesture for 1.5 seconds to trigger speech output
                    4. AI will recognize and speak the gesture

                    **Supported Signs:** Hello, Thank You, Please, Yes, No, Help, Sorry, Good, Bad, Water, Food, Medicine, Doctor, Emergency, Stop, Go, I, You, Love, Friend
                    """
                )

                with gr.Row():
                    with gr.Column():
                        video_input = gr.Image(
                            sources=["webcam"],
                            streaming=True,
                            label="Camera Feed",
                            type="numpy"
                        )

                    with gr.Column():
                        video_output = gr.Image(label="Detected Gestures")
                        gesture_text = gr.Textbox(
                            label="Recognized Gesture",
                            placeholder="Perform a gesture..."
                        )
                        confidence_text = gr.Number(
                            label="Confidence Score",
                            precision=2
                        )

                video_input.stream(
                    fn=app.process_frame,
                    inputs=video_input,
                    outputs=[video_output, gesture_text, confidence_text],
                    show_progress=False
                )

            # Tab 2: Text-to-Sign
            with gr.Tab("📝 Text to Sign"):
                gr.Markdown(
                    """
                    ### Coming Soon: Text to Sign Animation

                    Enter text below and it will be converted to sign language animation.
                    For the MVP, we'll speak the text and show a placeholder.

                    *Full 3D avatar animation coming in the next version!*
                    """
                )

                text_input = gr.Textbox(
                    label="Enter text to convert to sign language",
                    placeholder="Type something...",
                    lines=3
                )
                sign_output = gr.Textbox(
                    label="Sign Language Output",
                    lines=5
                )
                convert_btn = gr.Button("Convert to Sign", variant="primary")

                convert_btn.click(
                    fn=app.text_to_sign,
                    inputs=text_input,
                    outputs=sign_output
                )

            # Tab 3: Conversation History
            with gr.Tab("💬 Conversation History"):
                gr.Markdown("### View your recent sign language conversations with AI-powered summary")

                history_output = gr.Textbox(
                    label="Conversation Log with AI Summary",
                    lines=15,
                    max_lines=20
                )
                refresh_btn = gr.Button("Refresh History", variant="primary")

                refresh_btn.click(
                    fn=app.get_conversation_history,
                    outputs=history_output
                )

            # Tab 4: AI Learning Assistant
            with gr.Tab("🎓 Learning Assistant"):
                gr.Markdown(
                    """
                    ### Learn ASL with AI-Powered Explanations
                    Get detailed instructions on how to perform any ASL sign!
                    """
                )

                with gr.Row():
                    gesture_dropdown = gr.Dropdown(
                        choices=["Hello", "Thank You", "Please", "Yes", "No", "Help", "Sorry",
                                "Good", "Bad", "Water", "Food", "Medicine", "Doctor",
                                "Emergency", "Stop", "Go", "I", "You", "Love", "Friend"],
                        label="Select a gesture to learn",
                        value="Hello"
                    )
                    custom_gesture = gr.Textbox(
                        label="Or enter custom gesture name",
                        placeholder="e.g., 'family', 'work', 'home'"
                    )

                explain_btn = gr.Button("Get Explanation", variant="primary")
                explanation_output = gr.Textbox(
                    label="How to Sign",
                    lines=8
                )

                def get_explanation(selected, custom):
                    gesture = custom if custom else selected
                    return app.get_gesture_explanation(gesture)

                explain_btn.click(
                    fn=get_explanation,
                    inputs=[gesture_dropdown, custom_gesture],
                    outputs=explanation_output
                )

            # Tab 5: AI Settings & Context
            with gr.Tab("⚙️ AI Settings"):
                gr.Markdown(
                    """
                    ### Configure AI Enhancement Features
                    Customize how OpenAI assists with translation and interpretation
                    """
                )

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Context Mode")
                        gr.Markdown("Set the conversation context for more accurate interpretations")

                        context_radio = gr.Radio(
                            choices=["casual", "medical", "legal", "educational", "emergency"],
                            value="casual",
                            label="Select Context Mode"
                        )
                        context_status = gr.Textbox(label="Status", value="Context: casual")

                        context_radio.change(
                            fn=app.set_context_mode,
                            inputs=context_radio,
                            outputs=context_status
                        )

                    with gr.Column():
                        gr.Markdown("#### AI Enhancement")
                        gr.Markdown("Toggle AI-powered context-aware enhancements")

                        ai_toggle = gr.Checkbox(
                            label="Enable AI Enhancement",
                            value=True
                        )
                        ai_status = gr.Textbox(label="Status", value="AI enhancement enabled")

                        ai_toggle.change(
                            fn=app.toggle_ai_enhancement,
                            inputs=ai_toggle,
                            outputs=ai_status
                        )

                gr.Markdown(
                    """
                    ---
                    #### What AI Enhancement Does:
                    - **Context-Aware Translation**: Interprets gestures based on conversation mode
                    - **Alternative Suggestions**: Provides alternatives when confidence is low
                    - **Emergency Detection**: Automatically detects emergency situations
                    - **Conversation Summaries**: Generates intelligent summaries of your conversations
                    - **Learning Assistance**: Detailed explanations of how to perform any sign
                    """
                )

            # Tab 4: About
            with gr.Tab("ℹ️ About"):
                gr.Markdown(
                    """
                    ## About SignSpeak AI

                    ### The Problem
                    285 million deaf and hard-of-hearing people worldwide face daily communication barriers:
                    - Cannot communicate with non-signing individuals
                    - Limited access to healthcare, education, employment
                    - Human interpreters cost $50-150/hour
                    - Not available 24/7 for spontaneous interactions

                    ### Our Solution
                    SignSpeak AI provides:
                    - ✅ Real-time sign language recognition
                    - ✅ Instant translation to text and speech
                    - ✅ Free and accessible on any device
                    - ✅ Available 24/7, anywhere

                    ### Technology Stack
                    - **Computer Vision**: OpenCV for hand tracking
                    - **Machine Learning**: Scikit-learn for gesture classification
                    - **AI Enhancement**: OpenAI GPT-4 for context-aware features
                    - **Text-to-Speech**: pyttsx3
                    - **Web Interface**: Gradio

                    ### Impact
                    - 🌍 Empowers 285M+ people worldwide
                    - 💰 Free alternative to expensive interpreters
                    - ⚡ Real-time communication anywhere
                    - 🏥 Better access to essential services

                    ### Future Roadmap
                    - 3D avatar for sign language animation
                    - Support for multiple sign languages (BSL, ISL, etc.)
                    - Offline mode for emergency situations
                    - Mobile app for iOS and Android
                    - Learning module with practice feedback

                    ---

                    **Built for Horizon Hacks 2025 - AI for Accessibility and Equity**

                    Made with ❤️ for the deaf and hard-of-hearing community
                    """
                )

        gr.Markdown(
            """
            ---
            ### Tips for Best Results
            - Ensure good lighting
            - Keep hand clearly visible in camera
            - Perform gestures slowly and deliberately
            - Hold gesture for 1.5 seconds for speech output
            """
        )

    return interface


if __name__ == "__main__":
    print("=" * 60)
    print("SignSpeak AI - Real-time Sign Language Translation")
    print("=" * 60)
    print("\nInitializing application...")

    interface = create_interface()

    print("\nStarting web interface...")
    print("Access the app at: http://localhost:7860")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    interface.launch(
        share=True,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )
