from pathlib import Path
import joblib
import numpy as np
import torch
import time

from .emotion_buffer import EmotionBuffer


# ------------------------------------------------------------
# Import EmotionLSTM
# ------------------------------------------------------------

try:
    from Models.emotion_lstm import EmotionLSTM

except ImportError:

    try:
        from src.Models.emotion_lstm import EmotionLSTM

    except ImportError as e:

        raise ImportError(
            "Could not import EmotionLSTM. "
            "Make sure emotion_lstm.py is available."
        ) from e


class EmotionService:

    def __init__(self):

        # =====================================================
        # DEVICE
        # =====================================================

        self.device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print(
            f"Loading emotion model on {self.device}"
        )

        # =====================================================
        # PROJECT ROOT
        # =====================================================

        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        # =====================================================
        # PATHS
        # =====================================================

        model_path = (
            project_root /
            "best_emotion_lstm.pth"
        )

        scaler_path = (
            project_root /
            "gaze_scaler.pkl"
        )

        # =====================================================
        # SEQUENCE SETTINGS
        # =====================================================

        self.sequence_length = 30

        # Predict every 10 new frames.
        #
        # This gives overlapping sequences:
        #
        # 1-30
        # 11-40
        # 21-50
        # 31-60
        #
        self.prediction_stride = 10

        self.buffer = EmotionBuffer(
            sequence_length=self.sequence_length
        )

        self.frames_since_prediction = 0

        # =====================================================
        # 10 SECOND WINDOW
        # =====================================================

        self.window_duration = 10.0

        self.window_predictions = []

        self.window_start = None

        # =====================================================
        # CHECK FILES
        # =====================================================

        if not model_path.exists():

            raise FileNotFoundError(
                f"Emotion weights not found:\n"
                f"{model_path}"
            )

        if not scaler_path.exists():

            raise FileNotFoundError(
                f"Emotion scaler not found:\n"
                f"{scaler_path}"
            )

        # =====================================================
        # MODEL
        # =====================================================

        self.model = EmotionLSTM(
            input_size=3,
            hidden_size=64,
            num_layers=2,
            num_classes=4,
            dropout=0.2
        )

        state_dict = torch.load(
            model_path,
            map_location=self.device
        )

        self.model.load_state_dict(
            state_dict
        )

        self.model.to(
            self.device
        )

        self.model.eval()

        # =====================================================
        # SCALER
        # =====================================================

        self.scaler = joblib.load(
            scaler_path
        )

        # =====================================================
        # LABELS
        # =====================================================

        self.emotion_labels = {

            0: "Neutral",

            1: "Frustrated",

            2: "Bored",

            3: "Confident"
        }

        print(
            "Emotion model loaded successfully."
        )

        print(
            f"Sequence length : "
            f"{self.sequence_length}"
        )

        print(
            f"Prediction stride : "
            f"{self.prediction_stride} frames"
        )

        print(
            f"Aggregation window : "
            f"{self.window_duration} seconds"
        )

    # =========================================================
    # PREDICT
    # =========================================================

    def predict(self, sequence):

        sequence = np.asarray(
            sequence,
            dtype=np.float32
        )

        expected_shape = (
            self.sequence_length,
            3
        )

        if sequence.shape != expected_shape:

            raise ValueError(
                f"Expected sequence shape "
                f"{expected_shape}, "
                f"got {sequence.shape}"
            )

        if not np.all(
            np.isfinite(sequence)
        ):

            raise ValueError(
                "Emotion sequence contains "
                "NaN or infinite values."
            )

        # =====================================================
        # SCALE
        # =====================================================

        sequence_scaled = (
            self.scaler.transform(
                sequence
            )
        )

        # =====================================================
        # TENSOR
        # =====================================================

        tensor = torch.tensor(
            sequence_scaled,
            dtype=torch.float32,
            device=self.device
        )

        tensor = tensor.unsqueeze(0)

        # =====================================================
        # INFERENCE
        # =====================================================

        with torch.inference_mode():

            logits = self.model(
                tensor
            )

            probabilities = torch.softmax(
                logits,
                dim=1
            )

        # =====================================================
        # PROBABILITIES
        # =====================================================

        probabilities_np = (
            probabilities[0]
            .detach()
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        predicted_class = int(
            np.argmax(
                probabilities_np
            )
        )

        emotion = self.emotion_labels[
            predicted_class
        ]

        confidence = float(
            probabilities_np[
                predicted_class
            ]
        )

        # =====================================================
        # RETURN
        # =====================================================

        return {

            "emotion":
                emotion,

            "emotion_id":
                predicted_class,

            "confidence":
                confidence,

            "probabilities":
                probabilities_np.tolist()
        }

    # =========================================================
    # PROCESS FRAME
    # =========================================================

    def process_frame(
        self,
        gaze_x,
        gaze_y,
        pupil_size
    ):

        # =====================================================
        # VALIDATE INPUT
        # =====================================================

        values = [
            gaze_x,
            gaze_y,
            pupil_size
        ]

        try:

            valid = all(
                np.isfinite(
                    float(value)
                )
                for value in values
            )

        except (
            TypeError,
            ValueError
        ):

            valid = False

        if not valid:

            return {

                "ready": False,

                "overall_ready": False,

                "frames_collected":
                    self.buffer.size(),

                "required_frames":
                    self.sequence_length,

                "elapsed_seconds":
                    self._get_elapsed(),

                "predictions_collected":
                    len(
                        self.window_predictions
                    )
            }

        # =====================================================
        # START WINDOW
        # =====================================================

        if self.window_start is None:

            self.window_start = (
                time.monotonic()
            )

        # =====================================================
        # ADD FRAME
        # =====================================================

        self.buffer.add_frame(

            gaze_x=gaze_x,

            gaze_y=gaze_y,

            pupil_size=pupil_size
        )

        self.frames_since_prediction += 1

        # =====================================================
        # NOT ENOUGH FRAMES
        # =====================================================

        if not self.buffer.is_ready():

            return {

                "ready": False,

                "overall_ready": False,

                "frames_collected":
                    self.buffer.size(),

                "required_frames":
                    self.sequence_length,

                "elapsed_seconds":
                    self._get_elapsed(),

                "predictions_collected":
                    len(
                        self.window_predictions
                    )
            }

        # =====================================================
        # PREDICTION STRIDE
        # =====================================================

        if (
            self.frames_since_prediction
            < self.prediction_stride
        ):

            return {

                "ready": False,

                "overall_ready": False,

                "frames_collected":
                    self.buffer.size(),

                "required_frames":
                    self.sequence_length,

                "elapsed_seconds":
                    self._get_elapsed(),

                "predictions_collected":
                    len(
                        self.window_predictions
                    )
            }

        # =====================================================
        # GET SEQUENCE
        # =====================================================

        sequence = (
            self.buffer.get_sequence()
        )

        # =====================================================
        # MODEL PREDICTION
        # =====================================================

        result = self.predict(
            sequence
        )

        # Reset stride counter.
        self.frames_since_prediction = 0

        # =====================================================
        # STORE PREDICTION
        # =====================================================

        self.window_predictions.append(
            result
        )

        # =====================================================
        # CHECK WINDOW
        # =====================================================

        elapsed = (
            self._get_elapsed()
        )

        if elapsed < self.window_duration:

            return {

                "ready": True,

                "overall_ready": False,

                "emotion":
                    result["emotion"],

                "confidence":
                    result["confidence"],

                "probabilities":
                    result["probabilities"],

                "elapsed_seconds":
                    elapsed,

                "predictions_collected":
                    len(
                        self.window_predictions
                    ),

                "frames_collected":
                    self.buffer.size(),

                "required_frames":
                    self.sequence_length
            }

        # =====================================================
        # AGGREGATE
        # =====================================================

        overall_result = (
            self._aggregate_predictions()
        )

        # =====================================================
        # RESET
        # =====================================================

        self.window_predictions.clear()

        self.buffer.clear()

        self.frames_since_prediction = 0

        self.window_start = (
            time.monotonic()
        )

        # =====================================================
        # RETURN FINAL
        # =====================================================

        return {

            "ready": True,

            "overall_ready": True,

            **overall_result
        }

    # =========================================================
    # ELAPSED
    # =========================================================

    def _get_elapsed(self):

        if self.window_start is None:

            return 0.0

        return (
            time.monotonic()
            - self.window_start
        )

    # =========================================================
    # AGGREGATION
    # =========================================================

    def _aggregate_predictions(self):

        if not self.window_predictions:

            return {

                "emotion":
                    "No reliable prediction",

                "emotion_id":
                    -1,

                "confidence":
                    0.0,

                "probabilities":
                    [0.0, 0.0, 0.0, 0.0],

                "predictions_used":
                    0
            }

        # =====================================================
        # COLLECT PROBABILITY VECTORS
        # =====================================================

        probability_vectors = []

        for prediction in (
            self.window_predictions
        ):

            probability_vectors.append(
                np.asarray(
                    prediction["probabilities"],
                    dtype=np.float32
                )
            )

        # =====================================================
        # MEAN PROBABILITY
        # =====================================================

        mean_probabilities = (
            np.mean(
                probability_vectors,
                axis=0
            )
        )

        # =====================================================
        # NORMALIZE
        # =====================================================

        probability_sum = float(
            np.sum(
                mean_probabilities
            )
        )

        if probability_sum > 0:

            mean_probabilities = (
                mean_probabilities
                /
                probability_sum
            )

        # =====================================================
        # FINAL CLASS
        # =====================================================

        overall_emotion_id = int(
            np.argmax(
                mean_probabilities
            )
        )

        overall_emotion = (
            self.emotion_labels[
                overall_emotion_id
            ]
        )

        overall_confidence = float(
            mean_probabilities[
                overall_emotion_id
            ]
        )

        # =====================================================
        # DIAGNOSTICS
        # =====================================================

        print(
            "\n"
            + "-" * 60
        )

        print(
            "10-SECOND WINDOW PREDICTION DIAGNOSTICS"
        )

        print(
            "-" * 60
        )

        for index, prediction in enumerate(
            self.window_predictions,
            start=1
        ):

            print(
                f"Prediction {index:02d}: "
                f"{prediction['emotion']:<12} "
                f"| confidence="
                f"{prediction['confidence']:.6f}"
            )

        print(
            "\nAverage probabilities:"
        )

        for emotion_id, label in (
            self.emotion_labels.items()
        ):

            print(
                f"  {label:<12}: "
                f"{mean_probabilities[emotion_id]:.6f}"
            )

        print(
            "\nFinal aggregation:"
        )

        print(
            f"  Emotion     : "
            f"{overall_emotion}"
        )

        print(
            f"  Confidence  : "
            f"{overall_confidence:.6f}"
        )

        print(
            f"  Predictions : "
            f"{len(self.window_predictions)}"
        )

        print(
            "-" * 60
        )

        # =====================================================
        # RETURN
        # =====================================================

        return {

            "emotion":
                overall_emotion,

            "emotion_id":
                overall_emotion_id,

            "confidence":
                overall_confidence,

            "probabilities":
                mean_probabilities.tolist(),

            "predictions_used":
                len(
                    self.window_predictions
                )
        }