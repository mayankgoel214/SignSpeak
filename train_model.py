"""
Model Training Script for SignSpeak AI
Train gesture classification model from collected data
"""

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import pickle
from collect_data import DataCollector
import matplotlib.pyplot as plt
import seaborn as sns


def train_gesture_model():
    """Train gesture classification model"""
    print("\n" + "="*60)
    print("SignSpeak AI - Model Training")
    print("="*60 + "\n")

    # Load data
    print("Loading training data...")
    collector = DataCollector()

    try:
        X, y, gesture_to_label = collector.load_all_data()
    except Exception as e:
        print(f"Error loading data: {e}")
        print("\nMake sure you've collected training data first!")
        print("Run: python collect_data.py")
        return

    if len(X) == 0:
        print("No training data found!")
        print("Please run 'python collect_data.py' first to collect samples.")
        return

    print(f"\nDataset Info:")
    print(f"  Total samples: {len(X)}")
    print(f"  Number of gestures: {len(set(y))}")
    print(f"  Features per sample: {X.shape[1]}")

    # Split data
    print("\nSplitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"  Training samples: {len(X_train)}")
    print(f"  Testing samples: {len(X_test)}")

    # Train model
    print("\nTraining Random Forest Classifier...")
    print("  This may take a few moments...")

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    print("✓ Training complete!")

    # Evaluate model
    print("\nEvaluating model performance...")

    # Training accuracy
    train_pred = model.predict(X_train)
    train_accuracy = accuracy_score(y_train, train_pred)

    # Testing accuracy
    test_pred = model.predict(X_test)
    test_accuracy = accuracy_score(y_test, test_pred)

    print(f"\nAccuracy Scores:")
    print(f"  Training Accuracy: {train_accuracy:.2%}")
    print(f"  Testing Accuracy:  {test_accuracy:.2%}")

    if train_accuracy - test_accuracy > 0.1:
        print("\n⚠ Warning: Model may be overfitting (train >> test accuracy)")
    elif test_accuracy > 0.85:
        print("\n✓ Excellent model performance!")
    elif test_accuracy > 0.70:
        print("\n✓ Good model performance")
    else:
        print("\n⚠ Model performance could be improved")
        print("  Try collecting more samples or adjusting parameters")

    # Detailed classification report
    label_to_gesture = {v: k for k, v in gesture_to_label.items()}
    gesture_names = [label_to_gesture[i] for i in sorted(label_to_gesture.keys())]

    print("\n" + "="*60)
    print("Detailed Classification Report:")
    print("="*60)
    print(classification_report(
        y_test,
        test_pred,
        target_names=gesture_names,
        zero_division=0
    ))

    # Confusion matrix
    cm = confusion_matrix(y_test, test_pred)

    # Feature importance
    feature_importance = model.feature_importances_
    print("\nTop 5 Most Important Features:")
    feature_names = [
        "Aspect Ratio", "Relative Area", "Center X", "Center Y",
        "Width Ratio", "Height Ratio", "Compactness", "Circularity"
    ]
    indices = np.argsort(feature_importance)[::-1][:5]
    for i, idx in enumerate(indices, 1):
        if idx < len(feature_names):
            print(f"  {i}. {feature_names[idx]}: {feature_importance[idx]:.4f}")

    # Save model
    print("\nSaving model...")
    model_data = {
        'model': model,
        'gesture_to_label': gesture_to_label,
        'label_to_gesture': label_to_gesture,
        'accuracy': test_accuracy,
        'feature_names': feature_names
    }

    with open("gesture_model.pkl", 'wb') as f:
        pickle.dump(model_data, f)

    print("✓ Model saved as 'gesture_model.pkl'")

    # Plot confusion matrix
    try:
        plt.figure(figsize=(12, 10))
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=gesture_names,
            yticklabels=gesture_names
        )
        plt.title('Confusion Matrix - Gesture Classification')
        plt.ylabel('True Gesture')
        plt.xlabel('Predicted Gesture')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight')
        print("✓ Confusion matrix saved as 'confusion_matrix.png'")
    except Exception as e:
        print(f"Could not create confusion matrix plot: {e}")

    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print("\nNext Steps:")
    print("1. Review the accuracy and classification report above")
    print("2. Check confusion_matrix.png to see which gestures are confused")
    print("3. If accuracy is low, collect more training samples")
    print("4. Run 'python app.py' to use the trained model")
    print("\nThe app will automatically load gesture_model.pkl on startup")


if __name__ == "__main__":
    train_gesture_model()
