"""
Quick test script for OpenAI integration
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai_assistant import get_assistant

def test_openai_features():
    """Test all OpenAI features"""
    print("=" * 60)
    print("Testing OpenAI Integration for SignSpeak AI")
    print("=" * 60)

    # Initialize assistant
    print("\n1. Initializing OpenAI Assistant...")
    try:
        assistant = get_assistant()
        if assistant:
            print("✓ OpenAI Assistant initialized successfully!")
        else:
            print("✗ Failed to initialize OpenAI Assistant")
            return
    except Exception as e:
        print(f"✗ Error: {e}")
        return

    # Test gesture explanation
    print("\n2. Testing Gesture Explanation...")
    try:
        explanation = assistant.explain_gesture("Hello")
        print(f"✓ Gesture Explanation for 'Hello':")
        print(f"  {explanation[:200]}...")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test text to sign instructions
    print("\n3. Testing Text-to-Sign Instructions...")
    try:
        instructions = assistant.speech_to_sign_instructions("I need help")
        print(f"✓ Sign Instructions for 'I need help':")
        print(f"  {instructions[:200]}...")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test context-aware enhancement
    print("\n4. Testing Context-Aware Enhancement...")
    try:
        assistant.set_context_mode("medical")
        enhanced = assistant.enhance_gesture_translation("Help", 0.85)
        print(f"✓ Enhanced Translation (medical context):")
        print(f"  Original: Help")
        print(f"  Enhanced: {enhanced.get('interpretation', 'N/A')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test conversation summary
    print("\n5. Testing Conversation Summary...")
    try:
        sample_history = [
            ("Hello", "10:00:00", 0.95),
            ("Help", "10:00:05", 0.88),
            ("Doctor", "10:00:10", 0.82),
            ("Medicine", "10:00:15", 0.79)
        ]
        summary = assistant.generate_conversation_summary(sample_history)
        print(f"✓ Conversation Summary:")
        print(f"  {summary[:200]}...")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test emergency detection
    print("\n6. Testing Emergency Detection...")
    try:
        emergency_gestures = ["Help", "Doctor", "Emergency", "Bad"]
        is_emergency, emergency_type, confidence, action = assistant.detect_emergency(emergency_gestures)
        print(f"✓ Emergency Detection:")
        print(f"  Is Emergency: {is_emergency}")
        print(f"  Type: {emergency_type}")
        print(f"  Confidence: {confidence:.1%}")
        print(f"  Recommended Action: {action}")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n" + "=" * 60)
    print("OpenAI Integration Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_openai_features()
