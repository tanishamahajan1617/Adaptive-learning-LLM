# src/services/emotion_state.py

import threading


class EmotionState:

    latest_emotion = None
    latest_confidence = 0.0
    latest_predictions = 0

    _lock = threading.Lock()

    @classmethod
    def update(
        cls,
        emotion,
        confidence=0.0,
        predictions=0
    ):
        with cls._lock:
            cls.latest_emotion = emotion
            cls.latest_confidence = float(confidence)
            cls.latest_predictions = int(predictions)

    @classmethod
    def get(cls):
        with cls._lock:
            return {
                "emotion": cls.latest_emotion,
                "confidence": cls.latest_confidence,
                "predictions": cls.latest_predictions
            }

    @classmethod
    def reset(cls):
        with cls._lock:
            cls.latest_emotion = None
            cls.latest_confidence = 0.0
            cls.latest_predictions = 0