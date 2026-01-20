# SignSpeak AI - Hackathon Submission Guide

## Horizon Hacks 2025 Submission Checklist

### Required Materials

- [x] Working prototype/proof of concept
- [x] Clear problem and solution description
- [ ] Demo video or screenshots
- [ ] GitHub repository link
- [ ] Devpost submission

---

## 1. Project Overview

### Problem Statement
285 million deaf and hard-of-hearing people worldwide face daily communication barriers when interacting with non-signing individuals. Current interpreter services cost $50-150/hour, require advance booking, and aren't available for spontaneous everyday interactions in healthcare, education, employment, and emergency situations.

### Solution
SignSpeak AI is a real-time, bidirectional sign language translation application powered by computer vision and AI. It enables seamless communication between deaf and hearing individuals through:
- Real-time ASL hand gesture recognition
- Sign-to-text and text-to-speech conversion
- Web-based interface accessible on any device with a camera
- Free and available 24/7

### Target Audience
- Deaf and hard-of-hearing individuals
- Healthcare providers, educators, employers
- Emergency responders
- Anyone who needs to communicate with sign language users

---

## 2. Technical Implementation

### Architecture

```
User Camera Input
    ↓
Hand Detection (OpenCV)
    ↓
Feature Extraction
    ↓
Gesture Classification (ML)
    ↓
Text Output + Speech (TTS)
```

### Tech Stack
- **Computer Vision**: OpenCV for hand detection
- **Machine Learning**: Scikit-learn Random Forest Classifier
- **Web Framework**: Gradio for user interface
- **Text-to-Speech**: pyttsx3
- **Language**: Python 3.13

### Key Features Implemented
1. ✅ Real-time hand detection using color-based segmentation
2. ✅ Feature extraction from hand contours (8 features)
3. ✅ Gesture classification with confidence scoring
4. ✅ Text-to-speech output
5. ✅ Conversation history tracking
6. ✅ Web-based interface
7. ✅ Support for 20 common ASL signs

### Code Structure
- `app.py`: Main Gradio application (300+ lines)
- `hand_detector.py`: Hand detection module (157 lines)
- `gesture_classifier.py`: ML classifier (130+ lines)
- `text_to_speech.py`: TTS module (70+ lines)
- `collect_data.py`: Data collection utility (250+ lines)
- `train_model.py`: Model training script (180+ lines)

---

## 3. How to Demo

### Quick Demo (5 minutes)
1. Start the application: `python app.py`
2. Open browser to `http://localhost:7860`
3. Navigate to "Sign to Speech" tab
4. Allow camera access
5. Perform ASL gestures:
   - Wave hand for "Hello"
   - Show open palm for "Stop"
   - Try different hand positions
6. Hold gesture for 1.5 seconds to hear speech output
7. Check conversation history in the third tab
8. Show "About" tab explaining impact

### Full Demo (10 minutes)
- Show the problem statement slides/statistics
- Demonstrate sign-to-speech with multiple gestures
- Show confidence scoring
- Demonstrate text-to-sign placeholder
- Display conversation history
- Explain future roadmap (3D avatar, multi-language, offline mode)
- Discuss social impact and accessibility benefits

---

## 4. Creating Demo Video/Screenshots

### Screenshots Needed

1. **Landing Page**
   - Capture the "About" tab showing problem & solution

2. **Sign Detection in Action**
   - Hand visible in camera
   - Bounding box around hand
   - Gesture text displayed
   - Confidence score visible

3. **Conversation History**
   - Show multiple recognized gestures
   - Timestamps and confidence scores

4. **Interface Overview**
   - All tabs visible
   - Clean, accessible UI

### Demo Video Script (2-3 minutes)

**Intro (15 sec)**
"Hi, I'm [name], and this is SignSpeak AI - a real-time sign language translator that breaks communication barriers for 285 million deaf and hard-of-hearing people worldwide."

**Problem (20 sec)**
"Today, deaf individuals struggle to communicate with non-signing people in healthcare, education, and emergency situations. Human interpreters cost $50-150 per hour and aren't available for spontaneous interactions."

**Solution (30 sec)**
"SignSpeak AI uses computer vision and machine learning to recognize ASL gestures in real-time and convert them to speech. It works on any device with a camera and is completely free."

**Demo (60 sec)**
- Show hand detection working
- Perform 3-4 different gestures
- Show confidence scores
- Demonstrate speech output
- Show conversation history

**Impact (20 sec)**
"SignSpeak AI empowers 285 million people with free, instant communication access. No more expensive interpreters or advance booking. Just point your camera and start signing."

**Outro (15 sec)**
"Built for Horizon Hacks 2025. Check out our GitHub repo for the code and try it yourself!"

### Recording Tips
- Use screen recording software (OBS, QuickTime, Windows Game Bar)
- Ensure good audio quality
- Good lighting for hand detection
- Clear, confident narration
- Keep it under 3 minutes
- Export in 1080p MP4

---

## 5. GitHub Repository Setup

### Repository Structure
```
signspeak-ai/
├── README.md              # Project overview (done)
├── SETUP.md              # Installation guide (done)
├── SUBMISSION_GUIDE.md   # This file
├── LICENSE               # MIT License
├── .gitignore            # Python gitignore
│
├── requirements.txt      # Dependencies
│
├── app.py                # Main application
├── hand_detector.py      # Hand detection
├── gesture_classifier.py # Classification
├── text_to_speech.py     # TTS engine
├── collect_data.py       # Data collection
├── train_model.py        # Model training
│
└── docs/                 # Documentation & assets
    ├── screenshots/      # Demo screenshots
    ├── demo_video.mp4    # Demo video
    └── architecture.png  # System diagram
```

### Create Repository
```bash
# Initialize git (if not already done)
git init

# Create .gitignore
echo "*.pkl
*.pyc
__pycache__/
data/
*.png
venv/
.env" > .gitignore

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: SignSpeak AI - Real-time sign language translation

- Implemented hand detection using OpenCV
- Created gesture classification system
- Built Gradio web interface
- Added text-to-speech functionality
- Included data collection and training scripts
- Support for 20+ common ASL signs

Built for Horizon Hacks 2025 - AI for Accessibility and Equity"

# Create GitHub repository (use GitHub CLI or web interface)
gh repo create signspeak-ai --public --source=. --remote=origin --push

# Or push to existing repo
git remote add origin https://github.com/YOUR_USERNAME/signspeak-ai.git
git branch -M main
git push -u origin main
```

---

## 6. Devpost Submission

### Project Title
"SignSpeak AI - Real-time Sign Language Translation"

### Tagline (max 60 chars)
"Breaking communication barriers with AI-powered sign language"

### Inspiration
"We were inspired by the 285 million deaf and hard-of-hearing individuals worldwide who face daily communication barriers. When we learned that professional interpreters cost $50-150/hour and aren't available 24/7, we knew AI could democratize access to sign language translation and empower millions to communicate freely."

### What it does
"SignSpeak AI is a real-time sign language translation application that uses computer vision and machine learning to bridge communication gaps. Users simply point their camera, perform ASL gestures, and the app:

1. Detects hands using computer vision
2. Recognizes ASL gestures with ML
3. Converts signs to text and speech
4. Tracks conversation history
5. Provides confidence scores for each recognition

The app supports 20+ common ASL signs including essential words like Hello, Help, Emergency, Doctor, Water, Food, and more."

### How we built it
"**Tech Stack:**
- Python 3.13 for core logic
- OpenCV for real-time hand detection using color-based segmentation
- Scikit-learn Random Forest Classifier for gesture recognition
- Gradio for the web interface
- pyttsx3 for text-to-speech conversion

**Development Process:**
1. Built hand detection module using HSV color space for skin detection
2. Extracted geometric features (aspect ratio, area, compactness, circularity)
3. Implemented gesture classification with confidence scoring
4. Created data collection tool for training custom models
5. Developed web interface with Gradio for accessibility
6. Integrated text-to-speech for real-time feedback

The entire application is ~1000+ lines of Python code with modular architecture for easy extension."

### Challenges we ran into
"**Technical Challenges:**
1. **Python 3.13 Compatibility**: MediaPipe (standard for hand tracking) doesn't support Python 3.13 yet, so we built a custom hand detection system using OpenCV
2. **Gesture Recognition**: ASL gestures are complex 3D movements - we simplified to 2D features while maintaining reasonable accuracy
3. **Real-time Performance**: Balancing detection accuracy with processing speed for smooth 30fps video
4. **Lighting Variations**: Skin-tone detection works differently under various lighting conditions

**Solutions:**
- Developed custom color-based hand detection as fallback
- Created extensible ML pipeline for future improvements
- Optimized feature extraction for real-time processing
- Added confidence scoring to handle uncertain predictions"

### Accomplishments that we're proud of
"1. **Built a working prototype in <7 days** that demonstrates real-time sign language recognition
2. **Created an accessible, user-friendly interface** that anyone can use without technical knowledge
3. **Developed a complete ML pipeline** including data collection, training, and deployment tools
4. **Overcame technical limitations** by building custom solutions when libraries weren't compatible
5. **Addressed a real social need** with potential impact for 285 million people worldwide
6. **Made it free and open-source** so others can contribute and improve the technology"

### What we learned
"**Technical Learnings:**
- Computer vision fundamentals for hand detection and tracking
- Feature engineering for gesture classification
- Real-time video processing optimization
- Gradio framework for rapid prototyping
- Machine learning model deployment

**Domain Learnings:**
- ASL gesture structure and complexity
- Accessibility challenges faced by deaf/hard-of-hearing community
- Importance of user-friendly interfaces for assistive technology
- Cost barriers to professional interpretation services

**Project Learnings:**
- Building MVPs quickly by focusing on core features
- Balancing technical complexity with time constraints
- Importance of documentation for accessibility
- Open-source development best practices"

### What's next for SignSpeak AI
"**Short-term (Next 3 months):**
1. Collect real training data from ASL users
2. Train production-ready ML model with 90%+ accuracy
3. Integrate MediaPipe when Python 3.13 support is available
4. Expand to 100+ common ASL signs
5. Add user feedback mechanism

**Medium-term (6-12 months):**
1. Implement 3D avatar for text-to-sign animation
2. Support for multiple sign languages (BSL, ISL, Auslan, etc.)
3. Mobile apps for iOS and Android
4. Offline mode with essential vocabulary
5. Learning module with practice feedback

**Long-term Vision:**
1. Real-time video call translation
2. Integration with healthcare systems
3. Educational partnerships with deaf schools
4. Community-driven model improvement
5. Free global deployment

**Impact Goal:**
Enable barrier-free communication for all 285 million deaf and hard-of-hearing people worldwide."

### Built With
```
python
opencv
scikit-learn
gradio
numpy
machine-learning
computer-vision
accessibility
assistive-technology
sign-language
asl
```

### Try it out
- GitHub: `https://github.com/YOUR_USERNAME/signspeak-ai`
- Demo Video: `[Upload to YouTube and add link]`

---

## 7. Final Checklist

### Before Submitting
- [ ] Test app thoroughly on clean environment
- [ ] Record demo video (2-3 minutes)
- [ ] Take screenshots of all features
- [ ] Update README with latest features
- [ ] Push all code to GitHub
- [ ] Make repository public
- [ ] Add LICENSE file (MIT)
- [ ] Test README installation instructions
- [ ] Write clear commit messages
- [ ] Create GitHub repository description
- [ ] Add topics/tags to GitHub repo
- [ ] Upload demo video to YouTube
- [ ] Create Devpost project
- [ ] Fill out all Devpost fields
- [ ] Add team members to Devpost
- [ ] Upload screenshots to Devpost
- [ ] Add video link to Devpost
- [ ] Add GitHub link to Devpost
- [ ] Review and submit before deadline

### Submission Deadline
**November 25, 2025 @ 12:00am EST**

**Current Date: November 18, 2025**
**Days Remaining: 7 days**

---

## 8. Judging Criteria Alignment

### Creativity (25%)
**How we excel:**
- Novel approach to accessibility using CV + ML
- User-friendly interface for non-technical users
- Innovative data collection system
- Extensible architecture for community contributions

### Traction and Impact (25%)
**How we excel:**
- Addresses 285 million people worldwide
- Free alternative to $50-150/hour interpreters
- Immediate usability with webcam
- Open-source for widespread adoption

### Innovation (25%)
**How we excel:**
- Custom hand detection for Python 3.13
- Complete ML pipeline (collection → training → deployment)
- Real-time gesture recognition
- Built-in model training capabilities

### Novelty (25%)
**How we excel:**
- Fresh approach to sign language translation
- Accessible web interface (no app install needed)
- Community-driven improvement model
- Focus on underserved communities

---

## 9. Additional Resources

### ASL Reference Materials
- https://www.startasl.com/
- https://www.handspeak.com/
- https://www.lifeprint.com/

### Accessibility Guidelines
- WCAG 2.1 guidelines
- Section 508 compliance
- Mobile accessibility standards

### Technical Documentation
- OpenCV docs: https://docs.opencv.org/
- Gradio docs: https://gradio.app/docs/
- Scikit-learn docs: https://scikit-learn.org/

---

## Contact & Support

**Discord**: https://discord.gg/QwS69Vuy
**Website**: https://www.stemfortomorrow.org/
**GitHub**: [Your repository URL]

---

**Good luck with your submission! 🚀**

Built with ❤️ for Horizon Hacks 2025 - AI for Accessibility and Equity
