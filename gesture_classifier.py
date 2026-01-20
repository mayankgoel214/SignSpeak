"""
Simple gesture classification using rule-based and ML approaches
"""

import numpy as np
import pickle
import os


class GestureClassifier:
    def __init__(self):
        """Initialize gesture classifier with predefined ASL signs"""
        self.gestures = {
            0: "Hello",
            1: "Thank You",
            2: "Please",
            3: "Yes",
            4: "No",
            5: "Help",
            6: "Sorry",
            7: "Good",
            8: "Bad",
            9: "Water",
            10: "Food",
            11: "Medicine",
            12: "Doctor",
            13: "Emergency",
            14: "Stop",
            15: "Go",
            16: "I",
            17: "You",
            18: "Love",
            19: "Friend"
        }

        # Create gesture_names list for easy access
        self.gesture_names = list(self.gestures.values())

        self.model = None
        self.load_model()

    def load_model(self):
        """Load pre-trained model if available"""
        model_path = "gesture_model.pkl"
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
            except Exception as e:
                print(f"Could not load model: {e}")
                self.model = None

    def save_model(self):
        """Save trained model"""
        if self.model is not None:
            with open("gesture_model.pkl", 'wb') as f:
                pickle.dump(self.model, f)

    def classify_gesture(self, features):
        """
        Classify gesture from hand features

        Args:
            features: Normalized hand landmark features

        Returns:
            gesture_name: Name of detected gesture
            confidence: Confidence score (0-1)
        """
        if features is None:
            return "No hand detected", 0.0

        # For demo purposes, use simple rule-based classification
        # In production, you would use a trained ML model

        if self.model is not None:
            try:
                prediction = self.model.predict([features])
                confidence = np.max(self.model.predict_proba([features]))
                gesture_id = prediction[0]
                gesture_name = self.gestures.get(gesture_id, "Unknown")
                return gesture_name, float(confidence)
            except Exception as e:
                print(f"Model prediction error: {e}")

        # Fallback: simple rule-based classification
        return self._rule_based_classification(features)

    def _rule_based_classification(self, features):
        """
        Simple rule-based gesture recognition
        This is a placeholder - in real implementation you'd use trained ML model

        Args:
            features: Hand landmark features

        Returns:
            gesture_name, confidence
        """
        # Extract key points for simple gesture detection
        # This is simplified - real ASL recognition needs proper ML training

        # For demo: randomly select from common gestures with varying confidence
        # In production, analyze actual hand shape and position

        # Simple heuristic: use feature variance to select gesture
        variance = np.var(features)

        if variance < 0.05:
            return "Stop", 0.75
        elif variance < 0.1:
            return "Hello", 0.80
        elif variance < 0.15:
            return "Thank You", 0.72
        elif variance < 0.2:
            return "Please", 0.68
        else:
            return "Help", 0.65

    def train_model(self, X_train, y_train):
        """
        Train gesture classification model

        Args:
            X_train: Training features (N x 42 array)
            y_train: Training labels (N array)
        """
        from sklearn.ensemble import RandomForestClassifier

        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )

        self.model.fit(X_train, y_train)
        self.save_model()

        return self.model

    def get_gesture_list(self):
        """Get list of all supported gestures"""
        return list(self.gestures.values())
