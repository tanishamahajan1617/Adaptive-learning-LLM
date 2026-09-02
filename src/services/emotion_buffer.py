from collections import deque


class EmotionBuffer:

    def __init__(
        self,
        sequence_length=30,
        stride=10
    ):

        self.sequence_length = sequence_length
        self.stride = stride

        self.buffer = deque(
            maxlen=sequence_length
        )

        # Frames received after the
        # last prediction
        self.frames_since_prediction = 0

    # =========================================================
    # ADD FRAME
    # =========================================================

    def add_frame(
        self,
        gaze_x,
        gaze_y,
        pupil_size
    ):

        self.buffer.append([
            float(gaze_x),
            float(gaze_y),
            float(pupil_size)
        ])

        self.frames_since_prediction += 1

    # =========================================================
    # CHECK BUFFER READY
    # =========================================================

    def is_ready(self):

        return (
            len(self.buffer)
            >= self.sequence_length
        )

    # =========================================================
    # CHECK WHETHER PREDICTION IS DUE
    # =========================================================

    def prediction_due(self):

        if not self.is_ready():
            return False

        return (
            self.frames_since_prediction
            >= self.stride
        )

    # =========================================================
    # GET SEQUENCE
    # =========================================================

    def get_sequence(self):

        if not self.is_ready():
            return None

        return list(self.buffer)

    # =========================================================
    # MARK PREDICTION
    # =========================================================

    def mark_prediction(self):

        self.frames_since_prediction = 0

    # =========================================================
    # CLEAR BUFFER
    # =========================================================

    def clear(self):

        self.buffer.clear()

        self.frames_since_prediction = 0

    # =========================================================
    # SIZE
    # =========================================================

    def size(self):

        return len(self.buffer)

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.clear()