# SignSpeak AI

**Real-time sign language translation powered by AI**

## Problem Statement

285 million deaf and hard-of-hearing people worldwide face daily communication barriers when interacting with non-signing individuals in healthcare, education, employment, and emergency situations. Current interpreter services cost $50-150/hour, require advance booking, and aren't available for spontaneous everyday interactions.

## Solution

SignSpeak AI is a real-time, bidirectional sign language translation application that uses computer vision and AI to enable seamless communication between deaf and hearing individuals. The app works on any smartphone camera and is accessible anywhere, anytime.

## Features

### MVP Features (Hackathon Demo)
- ✅ Real-time ASL hand gesture recognition
- ✅ Sign-to-text conversion with confidence scoring
- ✅ Text-to-speech output
- ✅ Web-based interface for easy access
- ✅ Support for 20+ common ASL signs

### Future Roadmap
- Speech-to-sign animation with 3D avatar
- Multi-sign language support (BSL, ISL, etc.)
- Offline mode with essential vocabulary
- Learning module with practice feedback
- Context-aware translation (medical, legal, casual)

## Tech Stack

- **Python 3.13** - Core language
- **OpenCV** - Hand detection and video processing
- **Scikit-learn** - Gesture classification model
- **Gradio** - Web interface
- **NumPy** - Numerical computations
- **pyttsx3** - Text-to-speech conversion

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/signspeak-ai.git
cd signspeak-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run the application
python app.py
```

Open your browser to `http://localhost:7860` to access the interface.

## How It Works

1. **Hand Detection**: OpenCV detects hands using color-based segmentation in real-time
2. **Feature Extraction**: Extracts geometric features (aspect ratio, area, compactness, circularity)
3. **Gesture Classification**: Machine learning model classifies the gesture into ASL signs
4. **Translation**: Converts recognized signs to text with confidence scoring
5. **Speech Output**: Text-to-speech engine speaks the translation

## Supported Signs (MVP)

Hello, Thank You, Please, Yes, No, Help, Sorry, Good, Bad, Water, Food, Medicine, Doctor, Emergency, Stop, Go, I, You, Love, Friend

## Demo

[Video demo will be added here]

## Impact

SignSpeak AI aims to:
- 🌍 Bridge communication gaps for 285M+ deaf/hard-of-hearing individuals
- 💰 Provide free alternative to expensive interpreter services ($50-150/hour)
- ⚡ Enable spontaneous, real-time communication anywhere
- 🏥 Improve access to healthcare, education, and emergency services
- 📱 Make sign language translation accessible on any device

## Team

[Your name and team members]

## Acknowledgments

Built for Horizon Hacks 2025 - AI for Accessibility and Equity

## License

MIT License
