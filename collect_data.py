"""
Data Collection Script for SignSpeak AI
Use this to collect training data for gesture classification
"""

import cv2
import numpy as np
import os
import json
from hand_detector import HandLandmarkDetector
import time


class DataCollector:
    def __init__(self, data_dir="data"):
        """Initialize data collector"""
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.processed_dir = os.path.join(data_dir, "processed")

        # Create directories
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

        self.hand_detector = HandLandmarkDetector()

        # Gesture labels
        self.gestures = [
            "Hello", "Thank You", "Please", "Yes", "No",
            "Help", "Sorry", "Good", "Bad", "Water",
            "Food", "Medicine", "Doctor", "Emergency", "Stop",
            "Go", "I", "You", "Love", "Friend"
        ]

    def collect_gesture_samples(self, gesture_name, num_samples=50):
        """
        Collect samples for a specific gesture

        Args:
            gesture_name: Name of the gesture
            num_samples: Number of samples to collect
        """
        print(f"\n{'='*60}")
        print(f"Collecting samples for: {gesture_name}")
        print(f"Target: {num_samples} samples")
        print(f"{'='*60}\n")

        cap = cv2.VideoCapture(0)
        samples_collected = 0
        features_list = []

        print("Instructions:")
        print("1. Position your hand to perform the gesture")
        print("2. Press SPACE to capture a sample")
        print("3. Press ESC to finish early")
        print("4. Try different angles, distances, and hand positions")
        print("\nPress SPACE when ready...\n")

        collecting = False

        while samples_collected < num_samples:
            ret, frame = cap.read()
            if not ret:
                break

            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)

            # Detect hands
            hands, annotated_frame = self.hand_detector.detect_hands(frame)

            # Extract features
            features = self.hand_detector.extract_features(hands)

            # Add text overlay
            status_color = (0, 255, 0) if features is not None else (0, 0, 255)
            cv2.putText(
                annotated_frame,
                f"Gesture: {gesture_name}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )
            cv2.putText(
                annotated_frame,
                f"Samples: {samples_collected}/{num_samples}",
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                status_color,
                2
            )
            cv2.putText(
                annotated_frame,
                "SPACE: Capture | ESC: Exit",
                (10, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2
            )

            if features is not None:
                cv2.putText(
                    annotated_frame,
                    "Hand Detected - Ready!",
                    (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

            cv2.imshow("Data Collection", annotated_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ESC
                print("\nCollection stopped early by user")
                break
            elif key == 32:  # SPACE
                if features is not None:
                    features_list.append(features.tolist())
                    samples_collected += 1
                    print(f"✓ Sample {samples_collected} captured")

                    # Visual feedback
                    cv2.putText(
                        annotated_frame,
                        "CAPTURED!",
                        (200, 200),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        2,
                        (0, 255, 0),
                        3
                    )
                    cv2.imshow("Data Collection", annotated_frame)
                    cv2.waitKey(200)
                else:
                    print("✗ No hand detected - try again")

        cap.release()
        cv2.destroyAllWindows()

        # Save collected data
        if features_list:
            self.save_gesture_data(gesture_name, features_list)
            print(f"\n✓ Saved {len(features_list)} samples for '{gesture_name}'")
        else:
            print(f"\n✗ No samples collected for '{gesture_name}'")

        return len(features_list)

    def save_gesture_data(self, gesture_name, features_list):
        """Save collected features to JSON file"""
        data = {
            "gesture": gesture_name,
            "num_samples": len(features_list),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "features": features_list
        }

        filename = os.path.join(
            self.processed_dir,
            f"{gesture_name.lower().replace(' ', '_')}.json"
        )

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def collect_all_gestures(self, samples_per_gesture=50):
        """Collect samples for all gestures"""
        print("\n" + "="*60)
        print("SignSpeak AI - Data Collection")
        print("="*60)
        print(f"\nWill collect {samples_per_gesture} samples for each of {len(self.gestures)} gestures")
        print(f"Total samples: {samples_per_gesture * len(self.gestures)}")
        print("\nTips for good data:")
        print("- Use different hand positions and angles")
        print("- Try different lighting conditions")
        print("- Vary distance from camera")
        print("- Ensure hand is clearly visible")

        input("\nPress ENTER to start...")

        total_collected = 0

        for i, gesture in enumerate(self.gestures, 1):
            print(f"\n[{i}/{len(self.gestures)}] Next gesture: {gesture}")
            input("Press ENTER when ready...")

            collected = self.collect_gesture_samples(gesture, samples_per_gesture)
            total_collected += collected

            if i < len(self.gestures):
                print("\nTake a short break if needed...")
                time.sleep(2)

        print("\n" + "="*60)
        print("Data Collection Complete!")
        print(f"Total samples collected: {total_collected}")
        print(f"Data saved in: {self.processed_dir}")
        print("="*60)
        print("\nNext step: Run 'python train_model.py' to train the model")

    def load_all_data(self):
        """Load all collected gesture data for training"""
        X = []  # Features
        y = []  # Labels

        gesture_to_label = {gesture: i for i, gesture in enumerate(self.gestures)}

        for gesture in self.gestures:
            filename = os.path.join(
                self.processed_dir,
                f"{gesture.lower().replace(' ', '_')}.json"
            )

            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)

                features_list = data['features']
                label = gesture_to_label[gesture]

                for features in features_list:
                    X.append(features)
                    y.append(label)

                print(f"✓ Loaded {len(features_list)} samples for '{gesture}'")
            else:
                print(f"✗ No data found for '{gesture}'")

        return np.array(X), np.array(y), gesture_to_label


def main():
    """Main function"""
    collector = DataCollector()

    print("\nSignSpeak AI - Data Collection Tool")
    print("="*60)
    print("\nOptions:")
    print("1. Collect samples for all gestures")
    print("2. Collect samples for specific gesture")
    print("3. Exit")

    choice = input("\nEnter your choice (1-3): ").strip()

    if choice == "1":
        samples = input("How many samples per gesture? (default: 50): ").strip()
        samples = int(samples) if samples.isdigit() else 50
        collector.collect_all_gestures(samples_per_gesture=samples)

    elif choice == "2":
        print("\nAvailable gestures:")
        for i, gesture in enumerate(collector.gestures, 1):
            print(f"{i}. {gesture}")

        idx = input("\nEnter gesture number: ").strip()
        if idx.isdigit() and 1 <= int(idx) <= len(collector.gestures):
            gesture = collector.gestures[int(idx) - 1]
            samples = input(f"How many samples for '{gesture}'? (default: 50): ").strip()
            samples = int(samples) if samples.isdigit() else 50
            collector.collect_gesture_samples(gesture, num_samples=samples)
        else:
            print("Invalid gesture number")

    else:
        print("Exiting...")


if __name__ == "__main__":
    main()
