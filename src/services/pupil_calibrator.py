import time
import numpy as np


class PupilCalibrator:
    def __init__(
        self,
        calibration_duration=8.0,
        min_samples=10,
        max_calibration_duration=30.0
    ):
        self.calibration_duration = calibration_duration
        self.min_samples = min_samples
        self.max_calibration_duration = max_calibration_duration

        self.samples = []

        self.is_calibrating = False
        self.is_calibrated = False

        self.calibration_start = None
        self.baseline = None

        self.min_pupil_size = 0.02
        self.max_pupil_size = 1.0

        self.last_message = ""

    # ---------------------------------------------------------
    # START CALIBRATION
    # ---------------------------------------------------------

    def start(self):
        self.samples.clear()

        self.is_calibrating = True
        self.is_calibrated = False

        self.calibration_start = None
        self.baseline = None

        self.last_message = ""

        print("\n" + "=" * 50)
        print("PUPIL CALIBRATION STARTED")
        print("=" * 50)
        print(f"Minimum samples : {self.min_samples}")
        print(f"Minimum duration: {self.calibration_duration}s")
        print(f"Maximum duration: {self.max_calibration_duration}s")
        print("=" * 50)

    # ---------------------------------------------------------
    # ADD SAMPLE
    # ---------------------------------------------------------

    def add_sample(self, pupil_size):

        if not self.is_calibrating:
            return False

        if pupil_size is None:
            return False

        try:
            value = float(pupil_size)
        except (TypeError, ValueError):
            return False

        if not np.isfinite(value):
            return False

        # Reject obviously invalid pupil measurements
        if value < self.min_pupil_size or value > self.max_pupil_size:
            return False

        # Start timer on FIRST VALID sample
        if self.calibration_start is None:
            self.calibration_start = time.monotonic()

            print(
                f"First calibration sample received: "
                f"{value:.6f}"
            )

        self.samples.append(value)

        print(
            f"Calibration sample "
            f"{len(self.samples)}/{self.min_samples}: "
            f"{value:.6f}"
        )

        return True

    # ---------------------------------------------------------
    # UPDATE CALIBRATION
    # ---------------------------------------------------------

    def update(self):

        if not self.is_calibrating:
            return False

        if self.calibration_start is None:
            return False

        elapsed = time.monotonic() - self.calibration_start
        sample_count = len(self.samples)

        # -----------------------------------------------------
        # IMPORTANT:
        # Do NOT fail just because 8 seconds have passed.
        #
        # We first need enough samples.
        # -----------------------------------------------------

        if sample_count < self.min_samples:

            # Still allow calibration to continue
            # until maximum timeout.
            if elapsed < self.max_calibration_duration:
                return False

            # Maximum timeout reached
            print("\n" + "=" * 50)
            print("PUPIL CALIBRATION FAILED")
            print("=" * 50)
            print(
                f"Only {sample_count}/{self.min_samples} "
                f"samples collected."
            )
            print("=" * 50)

            self.is_calibrating = False
            self.is_calibrated = False
            self.baseline = None

            self.last_message = (
                f"Calibration failed: "
                f"{sample_count}/{self.min_samples} samples."
            )

            return False

        # -----------------------------------------------------
        # We have enough samples.
        # Still wait for minimum duration.
        # -----------------------------------------------------

        if elapsed < self.calibration_duration:
            return False

        # Enough samples + enough time
        return self.finish()

    # ---------------------------------------------------------
    # FINISH CALIBRATION
    # ---------------------------------------------------------

    def finish(self):

        if not self.is_calibrating:
            return False

        sample_count = len(self.samples)

        if sample_count < self.min_samples:

            print(
                f"Calibration cannot finish: "
                f"{sample_count}/{self.min_samples} samples."
            )

            return False

        self.is_calibrating = False

        # Convert samples to numpy
        values = np.asarray(
            self.samples,
            dtype=np.float32
        )

        # Remove invalid values
        values = values[np.isfinite(values)]

        if len(values) < self.min_samples:

            self.is_calibrated = False
            self.baseline = None

            self.last_message = (
                "Calibration failed because "
                "too few valid samples remained."
            )

            print(self.last_message)

            return False

        # -----------------------------------------------------
        # Remove extreme outliers using IQR
        # -----------------------------------------------------

        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)

        iqr = q3 - q1

        if iqr > 1e-6:

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            filtered = values[
                (values >= lower) &
                (values <= upper)
            ]

        else:
            filtered = values

        # If filtering removed too many samples,
        # use original values.
        if len(filtered) < self.min_samples:
            filtered = values

        # -----------------------------------------------------
        # Baseline = median pupil size
        # -----------------------------------------------------

        self.baseline = float(
            np.median(filtered)
        )

        self.baseline = float(
            np.clip(
                self.baseline,
                self.min_pupil_size,
                self.max_pupil_size
            )
        )

        self.is_calibrated = True

        self.last_message = (
            f"Calibration successful. "
            f"Baseline={self.baseline:.6f}"
        )

        print("\n" + "=" * 50)
        print("PUPIL CALIBRATION SUCCESSFUL")
        print("=" * 50)
        print(f"Samples collected : {sample_count}")
        print(f"Valid samples     : {len(values)}")
        print(f"Filtered samples  : {len(filtered)}")
        print(f"Baseline          : {self.baseline:.6f}")
        print("=" * 50)

        return True

    # ---------------------------------------------------------
    # NORMALIZE PUPIL
    # ---------------------------------------------------------

    def normalize(self, pupil_size):

        if pupil_size is None:
            return None

        try:
            value = float(pupil_size)
        except (TypeError, ValueError):
            return None

        if not np.isfinite(value):
            return None

        if not self.is_calibrated:
            return None

        if self.baseline is None:
            return None

        if self.baseline <= 0:
            return None

        normalized = value / self.baseline

        if not np.isfinite(normalized):
            return None

        return float(normalized)

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    def get_status(self):

        elapsed = 0.0

        if (
            self.is_calibrating
            and self.calibration_start is not None
        ):
            elapsed = (
                time.monotonic()
                - self.calibration_start
            )

        if self.is_calibrating:

            progress = min(
                elapsed /
                max(
                    self.calibration_duration,
                    1e-6
                ),
                1.0
            )

        else:
            progress = 0.0

        return {
            "calibrating": self.is_calibrating,
            "calibrated": self.is_calibrated,
            "baseline": self.baseline,

            "samples": len(self.samples),
            "min_samples": self.min_samples,

            "elapsed": round(elapsed, 3),

            "duration": self.calibration_duration,
            "max_duration": self.max_calibration_duration,

            "progress": round(progress, 3),

            "message": self.last_message
        }

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------

    def reset(self):

        self.samples.clear()

        self.is_calibrating = False
        self.is_calibrated = False

        self.calibration_start = None
        self.baseline = None

        self.last_message = ""

        print("Pupil calibration reset.")