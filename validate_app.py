"""
Final validation script - checks if app can start successfully
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("SIGNSPEAK AI - FINAL VALIDATION")
print("=" * 70)

print("\n[1/5] Checking dependencies...")
try:
    import cv2
    import numpy as np
    import gradio as gr
    import pyttsx3
    from openai import OpenAI
    from dotenv import load_dotenv
    print("✅ All dependencies installed")
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

print("\n[2/5] Checking API key...")
try:
    load_dotenv()
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and len(api_key) > 50:
        print(f"✅ API key found ({api_key[:20]}...)")
    else:
        print("⚠️  API key not found or invalid")
        print("   App will work without AI features")
except Exception as e:
    print(f"⚠️  API key check failed: {e}")

print("\n[3/5] Checking core modules...")
try:
    from hand_detector import HandLandmarkDetector
    from gesture_classifier import GestureClassifier
    from text_to_speech import TextToSpeech
    from openai_assistant import get_assistant
    print("✅ All core modules importable")
except ImportError as e:
    print(f"❌ Module import failed: {e}")
    sys.exit(1)

print("\n[4/5] Initializing app components...")
try:
    detector = HandLandmarkDetector(max_hands=1, detection_con=0.7)
    classifier = GestureClassifier()
    tts = TextToSpeech()
    assistant = get_assistant()
    print("✅ All components initialized successfully")
except Exception as e:
    print(f"❌ Component initialization failed: {e}")
    sys.exit(1)

print("\n[5/5] Testing app creation...")
try:
    from app import SignSpeakApp, create_interface
    app = SignSpeakApp()
    print("✅ SignSpeakApp created successfully")

    print("\n   Creating Gradio interface...")
    interface = create_interface()
    print("✅ Gradio interface created successfully")

except Exception as e:
    print(f"❌ App creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
print("\n✅ ALL CHECKS PASSED!")
print("\nYour app is ready to launch!")
print("\nTo start the app, run:")
print("  python app.py")
print("\nThen open your browser to:")
print("  http://localhost:7860")
print("\n" + "=" * 70)
