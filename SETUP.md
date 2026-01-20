# SignSpeak AI - Setup Guide

## Quick Start

### 1. Prerequisites
- Python 3.11 or later (tested on Python 3.13)
- Webcam for sign language detection
- Windows, macOS, or Linux

### 2. Installation

```bash
# Navigate to project directory
cd "signspeak-ai"

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python app.py
```

The application will start on `http://localhost:7860`

Open your browser and navigate to the URL to use the app.

## Features Available in MVP

### ✅ Sign to Speech
- Real-time hand detection using webcam
- Gesture recognition for 20+ common ASL signs
- Text-to-speech output
- Confidence scoring
- Conversation history tracking

### ✅ Text to Sign (Basic)
- Text input interface
- Text-to-speech output
- Placeholder for future sign language animation

## Supported ASL Signs (MVP)

The current MVP recognizes these common ASL signs:

1. Hello
2. Thank You
3. Please
4. Yes
5. No
6. Help
7. Sorry
8. Good
9. Bad
10. Water
11. Food
12. Medicine
13. Doctor
14. Emergency
15. Stop
16. Go
17. I
18. You
19. Love
20. Friend

## How to Use

### Sign to Speech Mode

1. Click on the "Sign to Speech" tab
2. Allow camera access when prompted
3. Position your hand in front of the camera
4. Perform ASL gestures
5. Hold the gesture for 1.5 seconds
6. The app will:
   - Detect your hand
   - Recognize the gesture
   - Display the recognized sign
   - Show confidence score
   - Speak the word aloud

### Tips for Best Results

- **Lighting**: Ensure good, even lighting on your hand
- **Background**: Use a plain background for better detection
- **Hand Position**: Keep your entire hand visible in the camera
- **Gesture Hold**: Hold each gesture steady for 1.5 seconds
- **Distance**: Position your hand 1-2 feet from the camera
- **Skin Tone**: The current algorithm works best with good lighting regardless of skin tone

## Troubleshooting

### Camera not working
- Check browser permissions for camera access
- Try refreshing the page
- Ensure no other app is using the camera

### Hand not detected
- Improve lighting conditions
- Move hand closer/further from camera
- Use a plain background
- Ensure hand is fully visible

### Low confidence scores
- Hold gesture more steadily
- Check that lighting is even
- Ensure proper hand positioning
- Practice the gesture from ASL reference materials

### Text-to-speech not working
- Check system audio settings
- Ensure speakers/headphones are connected
- On Windows: Ensure SAPI5 voices are installed
- On macOS: Ensure voices are installed in System Preferences
- On Linux: Install `espeak`: `sudo apt-get install espeak`

## Project Structure

```
signspeak-ai/
│
├── app.py                    # Main Gradio application
├── hand_detector.py          # Hand detection module (OpenCV-based)
├── gesture_classifier.py     # Gesture classification
├── text_to_speech.py        # Text-to-speech engine
│
├── requirements.txt          # Python dependencies
├── README.md                # Project overview
├── SETUP.md                 # This file
│
└── data/                    # (Optional) Training data directory
    ├── raw/                 # Raw gesture samples
    └── processed/           # Processed features
```

## Known Limitations (MVP)

1. **Hand Detection**: Uses color-based detection (skin tone) which may require good lighting
2. **Gesture Recognition**: Uses simple rule-based classification for demo purposes
3. **Sign Language Support**: Currently ASL only
4. **Accuracy**: MVP uses basic features; full ML model requires training data
5. **Avatar Animation**: Not implemented in MVP (planned for future)

## Next Steps for Improvement

### For Better Accuracy
1. Collect training data using the data collection script
2. Train ML model with collected data
3. Replace rule-based classifier with trained model

### For More Features
1. Implement 3D avatar for sign-to-text animation
2. Add support for more sign languages (BSL, ISL, etc.)
3. Implement offline mode
4. Add learning module
5. Create mobile apps (iOS/Android)

## Training Custom Model (Advanced)

To train a custom gesture classification model:

```bash
# 1. Collect training data
python collect_data.py

# 2. Train model
python train_model.py

# 3. The trained model will be saved as gesture_model.pkl
# 4. Restart the app to use the new model
```

## Support

For issues or questions:
- Check the GitHub Issues page
- Review the README.md for more information
- Join our Discord community (link in README)

## License

MIT License - See LICENSE file for details
