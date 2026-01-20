"""
Simplified hand detection using OpenCV and color-based detection
For Python 3.13 compatibility (MediaPipe not yet supported)
"""

import cv2
import numpy as np


class HandLandmarkDetector:
    def __init__(self, max_hands=1, detection_con=0.8):
        """
        Initialize simplified hand detector using color-based detection

        Args:
            max_hands: Maximum number of hands to detect
            detection_con: Detection confidence threshold (0-1)
        """
        self.max_hands = max_hands
        self.detection_con = detection_con

    def detect_hands(self, frame):
        """
        Detect hands in a frame using skin color detection

        Args:
            frame: Input image/frame

        Returns:
            hands: List with hand detection info
            annotated_frame: Frame with hand region highlighted
        """
        if frame is None:
            return [], frame

        annotated_frame = frame.copy()

        # Convert to HSV for better skin detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define skin color range in HSV
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        # Create mask for skin color
        mask = cv2.inRange(hsv, lower_skin, upper_skin)

        # Apply morphological operations to reduce noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        hands = []

        if contours:
            # Get largest contour (assuming it's the hand)
            max_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(max_contour)

            # Only consider if area is large enough
            if area > 5000:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(max_contour)

                # Draw rectangle around hand
                cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Calculate center
                cx = x + w // 2
                cy = y + h // 2

                # Draw center point
                cv2.circle(annotated_frame, (cx, cy), 5, (255, 0, 0), -1)

                # Create hand dict
                hand_info = {
                    'bbox': (x, y, w, h),
                    'center': (cx, cy),
                    'area': area,
                    'contour': max_contour
                }

                hands.append(hand_info)

        return hands, annotated_frame

    def extract_features(self, hands):
        """
        Extract simple features from detected hand

        Args:
            hands: List of detected hands

        Returns:
            features: Feature vector for classification
        """
        if not hands or len(hands) == 0:
            return None

        hand = hands[0]

        # Extract simple geometric features
        x, y, w, h = hand['bbox']
        area = hand['area']
        cx, cy = hand['center']

        # Create feature vector:
        # - Aspect ratio
        # - Relative area
        # - Normalized center position
        aspect_ratio = w / max(h, 1)
        relative_area = area / (640 * 480)  # Assume 640x480 frame

        features = np.array([
            aspect_ratio,
            relative_area,
            cx / 640,
            cy / 480,
            w / 640,
            h / 480
        ], dtype=np.float32)

        # Add contour-based features
        contour = hand['contour']

        # Hull area ratio (compactness)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        compactness = area / max(hull_area, 1)

        # Perimeter
        perimeter = cv2.arcLength(contour, True)
        circularity = (4 * np.pi * area) / max(perimeter * perimeter, 1)

        # Add these features
        features = np.append(features, [compactness, circularity])

        return features

    def get_hand_bbox(self, hands):
        """
        Get bounding box of detected hand

        Args:
            hands: List of detected hands

        Returns:
            bbox: Bounding box coordinates (x, y, w, h)
        """
        if not hands or len(hands) == 0:
            return None

        return hands[0].get('bbox', None)
