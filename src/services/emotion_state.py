# src/services/emotion_state.py

class EmotionState:

    latest_emotion = None
    latest_confidence = 0.0
    latest_predictions = 0

    @classmethod
    def update(
        cls,
        emotion,
        confidence=0.0,
        predictions=0
    ):
        cls.latest_emotion = emotion
        cls.latest_confidence = confidence
        cls.latest_predictions = predictions

    @classmethod
    def get(cls):
        return {
            "emotion": cls.latest_emotion,
            "confidence": cls.latest_confidence,
            "predictions": cls.latest_predictions
        }