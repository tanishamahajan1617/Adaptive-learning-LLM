import os
import sys
import cv2
import time
import torch
import numpy as np
import albumentations as A

from albumentations.pytorch import ToTensorV2


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# MODEL IMPORTS
# ============================================================

try:

    from src.Models.eyesegementation_model import UNet
    from src.Models.gaze_model import GazeModel

except ImportError:

    try:

        from Models.eyesegementation_model import UNet
        from Models.gaze_model import GazeModel

    except ImportError as e:

        raise ImportError(
            "\nCould not import U-Net / GazeModel.\n"
            "Check src/Models/."
        ) from e


# ============================================================
# SERVICES
# ============================================================

from src.services.emotion_service import EmotionService
from src.services.pupil_calibrator import PupilCalibrator


# ============================================================
# MEDIAPIPE
# ============================================================

try:

    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

except ImportError as e:

    raise ImportError(
        "\nMediaPipe Tasks API could not be imported.\n"
        "Install MediaPipe with:\n"
        "pip install mediapipe"
    ) from e


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# WEIGHTS
# ============================================================

UNET_WEIGHTS = os.path.join(
    PROJECT_ROOT,
    "best_unet_model.pth"
)

GAZE_WEIGHTS = os.path.join(
    PROJECT_ROOT,
    "best_gaze_model.pth"
)

FACE_LANDMARKER_MODEL = os.path.join(
    PROJECT_ROOT,
    "src",
    "Models",
    "face_landmarker.task"
)


# ============================================================
# EMOTION CONFIGURATION
# ============================================================

EMOTION_CONFIDENCE_THRESHOLD = 0.70


# ============================================================
# HEADSET CONFIGURATION
# ============================================================

# True:
#     OV9281 / headset camera mode.
#     Fixed eye ROIs are used.
#
# False:
#     Normal webcam mode.
#     MediaPipe detects face and eyes.
#
# The ROIs below are NORMALIZED coordinates:
#
#     x1, y1, x2, y2
#
# where values are between 0 and 1.
#
# This means the same ROIs can work with different
# camera resolutions.
#
# IMPORTANT:
# These are INITIAL ROIs.
# They must eventually be calibrated against the
# actual OV9281 camera frame.

HEADSET_MODE = True

HEADSET_EYE_ROIS = {

    "left": (
        0.02,
        0.15,
        0.49,
        0.92
    ),

    "right": (
        0.51,
        0.15,
        0.98,
        0.92
    )

}


# ============================================================
# EYE LANDMARKS
# ============================================================

LEFT_EYE_INDICES = [
    33,
    133,
    160,
    159,
    158,
    157,
    173,
    246
]

RIGHT_EYE_INDICES = [
    362,
    263,
    387,
    386,
    385,
    384,
    398,
    466
]


# ============================================================
# LIVE EMOTION PIPELINE
# ============================================================

class LiveEmotionPipeline:

    def __init__(
        self,
        camera_index=None,
        headset_mode=HEADSET_MODE
    ):

        print("=" * 60)
        print("Initializing Live Emotion Pipeline")
        print("=" * 60)

        print(
            f"Project root: {PROJECT_ROOT}"
        )

        print(
            f"Device: {DEVICE}"
        )

        print(
            f"Headset mode: {headset_mode}"
        )

        self.headset_mode = headset_mode

        # ====================================================
        # HEADSET ROI CHECK
        # ====================================================

        if self.headset_mode:

            left_roi = HEADSET_EYE_ROIS.get(
                "left"
            )

            right_roi = HEADSET_EYE_ROIS.get(
                "right"
            )

            if (
                left_roi is None
                or right_roi is None
            ):

                print("\nWARNING:")
                print(
                    "Headset mode is enabled, but "
                    "HEADSET_EYE_ROIS are not configured."
                )

                print(
                    "The pipeline will start, but "
                    "eye processing will not work."
                )

            else:

                print(
                    f"Left ROI: {left_roi}"
                )

                print(
                    f"Right ROI: {right_roi}"
                )

        # ====================================================
        # GPU INFORMATION
        # ====================================================

        if DEVICE.type == "cuda":

            print(
                f"GPU: "
                f"{torch.cuda.get_device_name(0)}"
            )

            print(
                f"CUDA: "
                f"{torch.version.cuda}"
            )

        # ====================================================
        # FILE CHECKS
        # ====================================================

        self.check_file(
            UNET_WEIGHTS,
            "U-Net weights"
        )

        self.check_file(
            GAZE_WEIGHTS,
            "Gaze model weights"
        )

        # MediaPipe is required only for normal webcam mode.

        if not self.headset_mode:

            self.check_file(
                FACE_LANDMARKER_MODEL,
                "MediaPipe Face Landmarker model"
            )

        # ====================================================
        # U-NET
        # ====================================================

        print("\nLoading U-Net...")

        self.unet_model = UNet(
            in_channels=1,
            num_classes=4
        ).to(DEVICE)

        unet_state = torch.load(
            UNET_WEIGHTS,
            map_location=DEVICE
        )

        self.unet_model.load_state_dict(
            unet_state
        )

        self.unet_model.eval()

        print(
            "U-Net loaded successfully."
        )

        # ====================================================
        # GAZE MODEL
        # ====================================================

        print("\nLoading Gaze Model...")

        self.gaze_model = GazeModel().to(
            DEVICE
        )

        gaze_state = torch.load(
            GAZE_WEIGHTS,
            map_location=DEVICE
        )

        self.gaze_model.load_state_dict(
            gaze_state
        )

        self.gaze_model.eval()

        print(
            "Gaze Model loaded successfully."
        )

        # ====================================================
        # EMOTION SERVICE
        # ====================================================

        print("\nLoading Emotion Service...")

        self.emotion_service = EmotionService()

        print(
            "Emotion Service loaded successfully."
        )

        # ====================================================
        # PUPIL CALIBRATOR
        # ====================================================

        print("\nInitializing Pupil Calibrator...")

        self.pupil_calibrator = PupilCalibrator(
            calibration_duration=8.0,
            min_samples=10
        )

        print(
            "Pupil Calibrator initialized."
        )

        # ====================================================
        # MEDIAPIPE
        # ====================================================

        self.face_landmarker = None

        if not self.headset_mode:

            print("\nInitializing MediaPipe...")

            base_options = python.BaseOptions(
                model_asset_path=FACE_LANDMARKER_MODEL
            )

            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )

            self.face_landmarker = (
                vision.FaceLandmarker.create_from_options(
                    options
                )
            )

            print(
                "MediaPipe Face Landmarker "
                "initialized successfully."
            )

        else:

            print(
                "\nHeadset mode enabled."
            )

            print(
                "MediaPipe face detection will NOT "
                "be used."
            )

        # ====================================================
        # CAMERA
        # ====================================================

        self.camera = None

        if camera_index is not None:

            print(
                f"\nOpening camera "
                f"index {camera_index}..."
            )

            self.camera = cv2.VideoCapture(
                camera_index
            )

            if not self.camera.isOpened():

                self.camera.release()
                self.camera = None

                raise RuntimeError(
                    f"Could not open camera "
                    f"index {camera_index}."
                )

            self.camera.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                1280
            )

            self.camera.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                720
            )

            print(
                "Camera opened successfully."
            )

        else:

            print(
                "\nCamera disabled."
            )

            print(
                "Pipeline is running in "
                "EXTERNAL FRAME MODE."
            )

            print(
                "Frames must be supplied through "
                "process_frame(frame)."
            )

        # ====================================================
        # STATE
        # ====================================================

        self.last_face_warning = 0.0

        # Video route reads these values.

        self.last_overall_emotion = None

        self.last_overall_confidence = 0.0

        self.last_overall_predictions = 0

        self.total_frames = 0

        self.valid_frames = 0

        self.processing_times = []

        # ====================================================
        # POPUP STATE
        # ====================================================

        self.popup_emotion_consumed = False

        self.popup_emotion = None

        self.popup_confidence = 0.0

        # ====================================================
        # CALIBRATION STATE
        # ====================================================

        self.auto_calibration_started = False

        self.calibration_finished_message_shown = False

        print("=" * 60)

    # ========================================================
    # FILE CHECK
    # ========================================================

    @staticmethod
    def check_file(
        path,
        description
    ):

        if not os.path.exists(path):

            raise FileNotFoundError(
                f"\n{description} not found:\n"
                f"{path}"
            )

    # ========================================================
    # START CALIBRATION
    # ========================================================

    def start_pupil_calibration(self):

        self.pupil_calibrator.start()

        self.calibration_finished_message_shown = False

    # ========================================================
    # ENSURE CALIBRATION
    # ========================================================

    def ensure_calibration_started(self):

        if (
            not self.auto_calibration_started
            and not self.pupil_calibrator.is_calibrated
            and not self.pupil_calibrator.is_calibrating
        ):

            print(
                "\n============================================================"
            )

            print(
                "PUPIL CALIBRATION ARMED"
            )

            print(
                "Look normally at the screen."
            )

            print(
                "Keep your eyes open naturally."
            )

            print(
                "Waiting for valid pupil samples..."
            )

            print(
                "============================================================"
            )

            self.start_pupil_calibration()

            self.auto_calibration_started = True

    # ========================================================
    # UPDATE CALIBRATION
    # ========================================================

    def update_pupil_calibration(
        self,
        pupil_size
    ):

        calibrator = self.pupil_calibrator

        was_calibrating = (
            calibrator.is_calibrating
        )

        # ----------------------------------------------------
        # ADD VALID SAMPLE
        # ----------------------------------------------------

        if (
            calibrator.is_calibrating
            and pupil_size is not None
        ):

            calibrator.add_sample(
                pupil_size
            )

        # ----------------------------------------------------
        # UPDATE TIMER
        # ----------------------------------------------------

        calibration_finished = (
            calibrator.update()
        )

        # ----------------------------------------------------
        # JUST FINISHED
        # ----------------------------------------------------

        if (
            was_calibrating
            and calibration_finished
            and not calibrator.is_calibrating
        ):

            if calibrator.is_calibrated:

                print(
                    "\nPupil calibration successful."
                )

                # Start completely fresh
                # emotion collection.

                self.emotion_service.buffer.clear()

                self.emotion_service.window_predictions.clear()

                self.emotion_service.window_start = None

                self.last_overall_emotion = None

                self.last_overall_confidence = 0.0

                self.last_overall_predictions = 0

                self.popup_emotion_consumed = False

                self.popup_emotion = None

                self.popup_confidence = 0.0

                print(
                    "Emotion collection started."
                )

            else:

                print(
                    "\nPupil calibration failed."
                )

                print(
                    "Emotion collection will wait "
                    "for successful calibration."
                )

        return calibrator.get_status()

    # ========================================================
    # ENSURE BGR FRAME
    # ========================================================

    @staticmethod
    def ensure_bgr(frame):

        if frame is None:

            return None

        # Grayscale image:
        #
        # shape = (H, W)

        if len(frame.shape) == 2:

            return cv2.cvtColor(
                frame,
                cv2.COLOR_GRAY2BGR
            )

        # Single-channel image:
        #
        # shape = (H, W, 1)

        if (
            len(frame.shape) == 3
            and frame.shape[2] == 1
        ):

            return cv2.cvtColor(
                frame,
                cv2.COLOR_GRAY2BGR
            )

        # Standard BGR image:
        #
        # shape = (H, W, 3)

        if (
            len(frame.shape) == 3
            and frame.shape[2] == 3
        ):

            return frame

        raise ValueError(
            f"Unsupported frame shape: "
            f"{frame.shape}"
        )

    # ========================================================
    # FACE LANDMARK DETECTION
    # ========================================================

    def detect_face_landmarks(
        self,
        frame
    ):

        if self.face_landmarker is None:

            return None

        frame = self.ensure_bgr(
            frame
        )

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb
        )

        result = (
            self.face_landmarker.detect(
                mp_image
            )
        )

        if not result.face_landmarks:

            return None

        return result.face_landmarks[0]

    # ========================================================
    # EYE CROP USING MEDIAPIPE
    # ========================================================

    def crop_eye(
        self,
        frame,
        landmarks,
        eye_indices,
        margin=0.35
    ):

        height, width = frame.shape[:2]

        xs = []
        ys = []

        for index in eye_indices:

            landmark = landmarks[index]

            x = int(
                landmark.x * width
            )

            y = int(
                landmark.y * height
            )

            xs.append(x)
            ys.append(y)

        if not xs or not ys:

            return None, None

        x_min = max(
            0,
            min(xs)
        )

        x_max = min(
            width - 1,
            max(xs)
        )

        y_min = max(
            0,
            min(ys)
        )

        y_max = min(
            height - 1,
            max(ys)
        )

        eye_width = x_max - x_min

        eye_height = y_max - y_min

        if (
            eye_width <= 2
            or eye_height <= 2
        ):

            return None, None

        margin_x = int(
            eye_width * margin
        )

        margin_y = int(
            eye_height * margin
        )

        x_min = max(
            0,
            x_min - margin_x
        )

        x_max = min(
            width,
            x_max + margin_x
        )

        y_min = max(
            0,
            y_min - margin_y
        )

        y_max = min(
            height,
            y_max + margin_y
        )

        eye_crop = frame[
            y_min:y_max,
            x_min:x_max
        ]

        if eye_crop.size == 0:

            return None, None

        bbox = (
            x_min,
            y_min,
            x_max,
            y_max
        )

        return eye_crop, bbox

    # ========================================================
    # EYE CROP USING FIXED HEADSET ROI
    # ========================================================

    def crop_headset_eye(
        self,
        frame,
        roi
    ):

        if roi is None:

            return None, None

        h, w = frame.shape[:2]

        x1, y1, x2, y2 = roi

        # ----------------------------------------------------
        # NORMALIZED ROI
        # ----------------------------------------------------

        if all(
            0 <= value <= 1
            for value in roi
        ):

            x1 = int(
                x1 * w
            )

            y1 = int(
                y1 * h
            )

            x2 = int(
                x2 * w
            )

            y2 = int(
                y2 * h
            )

        # ----------------------------------------------------
        # PIXEL ROI
        # ----------------------------------------------------

        else:

            x1, y1, x2, y2 = map(
                int,
                roi
            )

        # ----------------------------------------------------
        # CLAMP COORDINATES
        # ----------------------------------------------------

        x1 = max(
            0,
            min(
                x1,
                w - 1
            )
        )

        x2 = max(
            0,
            min(
                x2,
                w
            )
        )

        y1 = max(
            0,
            min(
                y1,
                h - 1
            )
        )

        y2 = max(
            0,
            min(
                y2,
                h
            )
        )

        # ----------------------------------------------------
        # INVALID ROI
        # ----------------------------------------------------

        if (
            x2 <= x1
            or y2 <= y1
        ):

            return None, None

        # ----------------------------------------------------
        # CROP
        # ----------------------------------------------------

        eye_crop = frame[
            y1:y2,
            x1:x2
        ]

        if eye_crop.size == 0:

            return None, None

        # ----------------------------------------------------
        # BOUNDING BOX
        # ----------------------------------------------------

        bbox = (
            x1,
            y1,
            x2,
            y2
        )

        return (
            eye_crop,
            bbox
        )

    # ========================================================
    # HEADSET EYE DETECTION
    # ========================================================

    def detect_headset_eyes(
        self,
        frame
    ):

        left_roi = (
            HEADSET_EYE_ROIS.get(
                "left"
            )
        )

        right_roi = (
            HEADSET_EYE_ROIS.get(
                "right"
            )
        )

        # ----------------------------------------------------
        # LEFT EYE
        # ----------------------------------------------------

        left_eye_crop, left_bbox = (
            self.crop_headset_eye(
                frame,
                left_roi
            )
        )

        # ----------------------------------------------------
        # RIGHT EYE
        # ----------------------------------------------------

        right_eye_crop, right_bbox = (
            self.crop_headset_eye(
                frame,
                right_roi
            )
        )

        # IMPORTANT:
        #
        # process_frame() expects FOUR values.

        return (
            left_eye_crop,
            left_bbox,
            right_eye_crop,
            right_bbox
        )

    # ========================================================
    # U-NET SEGMENTATION
    # ========================================================

    def segment_eye(
        self,
        eye_crop
    ):

        if len(
            eye_crop.shape
        ) == 2:

            gray = eye_crop

        else:

            gray = cv2.cvtColor(
                eye_crop,
                cv2.COLOR_BGR2GRAY
            )

        transform = A.Compose([

            A.Resize(
                height=256,
                width=256
            ),

            A.Normalize(
                mean=(0.5,),
                std=(0.5,),
                max_pixel_value=255.0
            ),

            ToTensorV2()

        ])

        transformed = transform(
            image=gray
        )

        tensor = transformed[
            "image"
        ]

        tensor = (
            tensor
            .unsqueeze(0)
            .to(DEVICE)
            .float()
        )

        with torch.inference_mode():

            output = self.unet_model(
                tensor
            )

            mask = torch.argmax(
                output,
                dim=1
            )

        mask = (
            mask
            .squeeze(0)
            .cpu()
            .numpy()
        )

        original_h, original_w = (
            gray.shape
        )

        mask = cv2.resize(
            mask,
            (
                original_w,
                original_h
            ),
            interpolation=cv2.INTER_NEAREST
        )

        return mask

    # ========================================================
    # PUPIL MEASUREMENT
    # ========================================================

    def measure_pupil(
        self,
        mask
    ):

        # U-Net class mapping:
        #
        # 0 = background
        # 1 = sclera
        # 2 = iris
        # 3 = pupil

        pupil_mask = (
            mask == 3
        ).astype(
            np.uint8
        )

        contours, _ = cv2.findContours(
            pupil_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:

            return None, None

        largest_contour = max(
            contours,
            key=cv2.contourArea
        )

        area = cv2.contourArea(
            largest_contour
        )

        if area <= 0:

            return None, None

        diameter = (
            2.0
            *
            np.sqrt(
                area / np.pi
            )
        )

        return (
            float(diameter),
            largest_contour
        )

    # ========================================================
    # GAZE
    # ========================================================

    def predict_gaze(
        self,
        eye_crop
    ):

        # GazeModel was trained using RGB images.
        #
        # OV9281 may provide grayscale.
        #
        # Therefore:
        #
        # grayscale
        #     ↓
        # grayscale → RGB
        #     ↓
        # MobileNetV2

        if len(
            eye_crop.shape
        ) == 2:

            eye_rgb = cv2.cvtColor(
                eye_crop,
                cv2.COLOR_GRAY2RGB
            )

        else:

            eye_rgb = cv2.cvtColor(
                eye_crop,
                cv2.COLOR_BGR2RGB
            )

        transform = A.Compose([

            A.Resize(
                height=224,
                width=224
            ),

            A.Normalize(
                mean=(
                    0.5,
                    0.5,
                    0.5
                ),
                std=(
                    0.5,
                    0.5,
                    0.5
                ),
                max_pixel_value=255.0
            ),

            ToTensorV2()

        ])

        tensor = transform(
            image=eye_rgb
        )["image"]

        tensor = (
            tensor
            .unsqueeze(0)
            .to(DEVICE)
            .float()
        )

        with torch.inference_mode():

            output = self.gaze_model(
                tensor
            )

        coords = (
            output
            .cpu()
            .numpy()
            .flatten()
        )

        if len(coords) < 2:

            raise ValueError(
                "Gaze model returned "
                f"unexpected shape: "
                f"{coords.shape}"
            )

        gaze_x = float(
            np.clip(
                coords[0],
                0.0,
                1.0
            )
        )

        gaze_y = float(
            np.clip(
                coords[1],
                0.0,
                1.0
            )
        )

        return (
            gaze_x,
            gaze_y
        )

    # ========================================================
    # PROCESS SINGLE EYE
    # ========================================================

    def process_eye(
        self,
        eye_crop
    ):

        if eye_crop is None:

            raise ValueError(
                "Eye crop is None."
            )

        # ----------------------------------------------------
        # SEGMENTATION
        # ----------------------------------------------------

        mask = self.segment_eye(
            eye_crop
        )

        # ----------------------------------------------------
        # PUPIL
        # ----------------------------------------------------

        pupil_diameter, pupil_contour = (
            self.measure_pupil(
                mask
            )
        )

        # ----------------------------------------------------
        # GAZE
        # ----------------------------------------------------

        gaze_x, gaze_y = (
            self.predict_gaze(
                eye_crop
            )
        )

        # ----------------------------------------------------
        # EYE SIZE
        # ----------------------------------------------------

        if len(
            eye_crop.shape
        ) == 2:

            eye_height, eye_width = (
                eye_crop.shape
            )

        else:

            eye_height, eye_width, _ = (
                eye_crop.shape
            )

        # ----------------------------------------------------
        # NORMALIZED PUPIL SIZE
        # ----------------------------------------------------

        if (
            pupil_diameter is not None
            and eye_width > 0
        ):

            pupil_size = (
                pupil_diameter
                / float(eye_width)
            )

            if not np.isfinite(
                pupil_size
            ):

                pupil_size = None

        else:

            pupil_size = None

        return {

            "mask":
                mask,

            "gaze_x":
                gaze_x,

            "gaze_y":
                gaze_y,

            "pupil_diameter":
                pupil_diameter,

            "pupil_size":
                pupil_size,

            "pupil_contour":
                pupil_contour
        }

    # ========================================================
    # EMPTY EMOTION RESULT
    # ========================================================

    def empty_emotion_result(self):

        return {

            "ready":
                False,

            "overall_ready":
                False,

            "emotion":
                self.last_overall_emotion,

            "confidence":
                self.last_overall_confidence,

            "frames_collected":
                self.emotion_service
                .buffer
                .size(),

            "required_frames":
                30,

            "predictions_collected":
                len(
                    self.emotion_service
                    .window_predictions
                ),

            "elapsed_seconds":
                self.get_window_elapsed(),

            "popup":
                False
        }

    # ========================================================
    # ADAPTATION
    # ========================================================

    def get_adaptation(
        self,
        emotion,
        confidence
    ):

        if emotion is None:

            return {

                "show_popup":
                    False,

                "adaptation":
                    None,

                "message":
                    None
            }

        if (
            confidence
            < EMOTION_CONFIDENCE_THRESHOLD
        ):

            return {

                "show_popup":
                    False,

                "adaptation":
                    None,

                "message":
                    None
            }

        if emotion == "Frustrated":

            return {

                "show_popup":
                    True,

                "adaptation":
                    "simpler_explanation",

                "message":
                    (
                        "This concept seems "
                        "a little difficult. "
                        "Would you like a "
                        "simpler explanation?"
                    )
            }

        if emotion == "Bored":

            return {

                "show_popup":
                    True,

                "adaptation":
                    "more_engaging_explanation",

                "message":
                    (
                        "It looks like you "
                        "might be losing interest. "
                        "Would you like a more "
                        "engaging explanation?"
                    )
            }

        return {

            "show_popup":
                False,

            "adaptation":
                None,

            "message":
                None
        }

    # ========================================================
    # UPDATE OVERALL EMOTION
    # ========================================================

    def update_overall_emotion(
        self,
        emotion_result
    ):

        if not emotion_result:

            return

        if not emotion_result.get(
            "overall_ready",
            False
        ):

            return

        emotion = (
            emotion_result.get(
                "emotion"
            )
        )

        confidence = float(
            emotion_result.get(
                "confidence",
                0.0
            )
        )

        predictions_used = int(
            emotion_result.get(
                "predictions_used",
                0
            )
        )

        # ----------------------------------------------------
        # STORE LATEST OVERALL RESULT
        # ----------------------------------------------------

        self.last_overall_emotion = (
            emotion
        )

        self.last_overall_confidence = (
            confidence
        )

        self.last_overall_predictions = (
            predictions_used
        )

        # ----------------------------------------------------
        # NEW POPUP DECISION
        # ----------------------------------------------------

        self.popup_emotion_consumed = False

        self.popup_emotion = emotion

        self.popup_confidence = confidence

    # ========================================================
    # GET POPUP INFORMATION
    # ========================================================

    def get_popup_state(self):

        if (
            self.popup_emotion_consumed
        ):

            return {

                "show_popup":
                    False,

                "emotion":
                    self.popup_emotion,

                "confidence":
                    self.popup_confidence,

                "adaptation":
                    None,

                "message":
                    None
            }

        adaptation = self.get_adaptation(
            self.popup_emotion,
            self.popup_confidence
        )

        return adaptation | {

            "emotion":
                self.popup_emotion,

            "confidence":
                self.popup_confidence
        }

    # ========================================================
    # ACKNOWLEDGE POPUP
    # ========================================================

    def acknowledge_popup(self):

        self.popup_emotion_consumed = True

        return {

            "success":
                True,

            "popup_consumed":
                True
        }

    # ========================================================
    # PROCESS FRAME
    # ========================================================

    def process_frame(
        self,
        frame
    ):

        if frame is None:

            raise ValueError(
                "Received empty frame."
            )

        if not isinstance(
            frame,
            np.ndarray
        ):

            raise TypeError(
                "frame must be "
                "a numpy ndarray."
            )

        self.total_frames += 1

        frame_start = (
            time.monotonic()
        )

        # ----------------------------------------------------
        # MAKE FRAME COMPATIBLE
        # ----------------------------------------------------

        frame = self.ensure_bgr(
            frame
        )

        # ----------------------------------------------------
        # START CALIBRATION
        # ----------------------------------------------------

        self.ensure_calibration_started()

        # ----------------------------------------------------
        # GET EYES
        # ----------------------------------------------------

        if self.headset_mode:

            (
                left_eye_crop,
                left_bbox,
                right_eye_crop,
                right_bbox
            ) = self.detect_headset_eyes(
                frame
            )

            # In headset mode there is no face detection.
            #
            # This is kept True for compatibility with the
            # existing API. The important field is
            # eyes_detected.

            face_detected = True

        else:

            landmarks = (
                self.detect_face_landmarks(
                    frame
                )
            )

            if landmarks is None:

                return {

                    "face_detected":
                        False,

                    "eyes_detected":
                        False,

                    "left_eye":
                        None,

                    "right_eye":
                        None,

                    "gaze_x":
                        None,

                    "gaze_y":
                        None,

                    "pupil_size":
                        None,

                    "normalized_pupil":
                        None,

                    "calibration":
                        self.pupil_calibrator
                        .get_status(),

                    "emotion":
                        self.empty_emotion_result(),

                    "overall_emotion":
                        self.last_overall_emotion,

                    "overall_confidence":
                        self.last_overall_confidence,

                    "popup":
                        self.get_popup_state()
                }

            face_detected = True

            left_eye_crop, left_bbox = (
                self.crop_eye(
                    frame,
                    landmarks,
                    LEFT_EYE_INDICES
                )
            )

            right_eye_crop, right_bbox = (
                self.crop_eye(
                    frame,
                    landmarks,
                    RIGHT_EYE_INDICES
                )
            )

        # ----------------------------------------------------
        # EYES DETECTED
        # ----------------------------------------------------

        if (
            left_eye_crop is None
            and right_eye_crop is None
        ):

            return {

                "face_detected":
                    face_detected,

                "eyes_detected":
                    False,

                "left_eye":
                    None,

                "right_eye":
                    None,

                "gaze_x":
                    None,

                "gaze_y":
                    None,

                "pupil_size":
                    None,

                "normalized_pupil":
                    None,

                "calibration":
                    self.pupil_calibrator
                    .get_status(),

                "emotion":
                    self.empty_emotion_result(),

                "overall_emotion":
                    self.last_overall_emotion,

                "overall_confidence":
                    self.last_overall_confidence,

                "popup":
                    self.get_popup_state()
            }

        # ----------------------------------------------------
        # PROCESS EYES
        # ----------------------------------------------------

        left_result = None

        right_result = None

        if left_eye_crop is not None:

            try:

                left_result = (
                    self.process_eye(
                        left_eye_crop
                    )
                )

            except Exception as e:

                print(
                    f"Left eye processing error: {e}"
                )

        if right_eye_crop is not None:

            try:

                right_result = (
                    self.process_eye(
                        right_eye_crop
                    )
                )

            except Exception as e:

                print(
                    f"Right eye processing error: {e}"
                )

        # ----------------------------------------------------
        # VALID EYES
        # ----------------------------------------------------

        valid_results = []

        if left_result is not None:

            valid_results.append(
                left_result
            )

        if right_result is not None:

            valid_results.append(
                right_result
            )

        if not valid_results:

            return {

                "face_detected":
                    face_detected,

                "eyes_detected":
                    True,

                "left_eye":
                    None,

                "right_eye":
                    None,

                "gaze_x":
                    None,

                "gaze_y":
                    None,

                "pupil_size":
                    None,

                "normalized_pupil":
                    None,

                "calibration":
                    self.pupil_calibrator
                    .get_status(),

                "emotion":
                    self.empty_emotion_result(),

                "overall_emotion":
                    self.last_overall_emotion,

                "overall_confidence":
                    self.last_overall_confidence,

                "popup":
                    self.get_popup_state()
            }

        # ----------------------------------------------------
        # GAZE
        # ----------------------------------------------------

        gaze_values_x = [

            result["gaze_x"]

            for result in valid_results

            if result.get(
                "gaze_x"
            ) is not None
        ]

        gaze_values_y = [

            result["gaze_y"]

            for result in valid_results

            if result.get(
                "gaze_y"
            ) is not None
        ]

        if gaze_values_x:

            gaze_x = float(
                np.mean(
                    gaze_values_x
                )
            )

        else:

            gaze_x = None

        if gaze_values_y:

            gaze_y = float(
                np.mean(
                    gaze_values_y
                )
            )

        else:

            gaze_y = None

        # ----------------------------------------------------
        # PUPIL
        # ----------------------------------------------------

        pupil_values = [

            result["pupil_size"]

            for result in valid_results

            if result.get(
                "pupil_size"
            ) is not None
        ]

        if pupil_values:

            # Median is robust against
            # one bad eye segmentation.

            raw_pupil_size = float(
                np.median(
                    pupil_values
                )
            )

        else:

            raw_pupil_size = None

        # ----------------------------------------------------
        # CALIBRATION
        # ----------------------------------------------------

        calibration_status = (
            self.update_pupil_calibration(
                raw_pupil_size
            )
        )

        # ----------------------------------------------------
        # NORMALIZE PUPIL
        # ----------------------------------------------------

        normalized_pupil = None

        if raw_pupil_size is not None:

            try:

                normalized_pupil = (
                    self.pupil_calibrator
                    .normalize(
                        raw_pupil_size
                    )
                )

            except Exception as e:

                print(
                    f"Pupil normalization error: {e}"
                )

                normalized_pupil = None

        # ----------------------------------------------------
        # EMOTION
        # ----------------------------------------------------

        emotion_result = (
            self.empty_emotion_result()
        )

        if (
            gaze_x is not None
            and gaze_y is not None
            and normalized_pupil is not None
            and self.pupil_calibrator.is_calibrated
        ):

            try:

                emotion_result = (
                    self.emotion_service.process_frame(

                        gaze_x=gaze_x,

                        gaze_y=gaze_y,

                        pupil_size=normalized_pupil
                    )
                )

                self.valid_frames += 1

                # --------------------------------------------
                # UPDATE LATEST OVERALL EMOTION
                # --------------------------------------------

                self.update_overall_emotion(
                    emotion_result
                )

            except Exception as e:

                print(
                    f"Emotion processing error: {e}"
                )

        # ----------------------------------------------------
        # POPUP STATE
        # ----------------------------------------------------

        popup_state = (
            self.get_popup_state()
        )

        emotion_result[
            "popup"
        ] = popup_state

        # ----------------------------------------------------
        # PROCESSING TIME
        # ----------------------------------------------------

        if DEVICE.type == "cuda":

            torch.cuda.synchronize()

        processing_time = (
            time.monotonic()
            - frame_start
        )

        self.processing_times.append(
            processing_time
        )

        if len(
            self.processing_times
        ) > 30:

            self.processing_times.pop(
                0
            )

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        return {

            "face_detected":
                face_detected,

            "eyes_detected":
                True,

            "left_eye": {

                "bbox":
                    left_bbox,

                "result":
                    left_result

            } if left_result is not None else None,

            "right_eye": {

                "bbox":
                    right_bbox,

                "result":
                    right_result

            } if right_result is not None else None,

            # Combined gaze

            "gaze_x":
                gaze_x,

            "gaze_y":
                gaze_y,

            # Combined pupil

            "pupil_size":
                raw_pupil_size,

            "normalized_pupil":
                normalized_pupil,

            # Calibration

            "calibration":
                calibration_status,

            # Current emotion window

            "emotion":
                emotion_result,

            # Latest overall emotion

            "overall_emotion":
                self.last_overall_emotion,

            "overall_confidence":
                self.last_overall_confidence,

            "overall_predictions":
                self.last_overall_predictions,

            # Popup

            "popup":
                popup_state,

            # Performance

            "processing_time":
                float(
                    processing_time
                )
        }

    # ========================================================
    # WINDOW ELAPSED
    # ========================================================

    def get_window_elapsed(self):

        start = (
            self.emotion_service
            .window_start
        )

        if start is None:

            return 0.0

        return (
            time.monotonic()
            - start
        )

    # ========================================================
    # DRAW EYE RESULT
    # ========================================================

    def draw_eye_result(
        self,
        frame,
        eye_data,
        label
    ):

        if eye_data is None:

            return

        bbox = eye_data.get(
            "bbox"
        )

        result = eye_data.get(
            "result"
        )

        if bbox is None:

            return

        x1, y1, x2, y2 = bbox

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            label,
            (
                x1,
                max(
                    20,
                    y1 - 8
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2
        )

        if result is None:

            return

        contour = result.get(
            "pupil_contour"
        )

        if contour is not None:

            contour_global = (
                contour.copy()
            )

            contour_global[:, :, 0] += x1

            contour_global[:, :, 1] += y1

            cv2.drawContours(
                frame,
                [contour_global],
                -1,
                (0, 255, 255),
                2
            )

    # ========================================================
    # DRAW CALIBRATION STATUS
    # ========================================================

    def draw_calibration_status(
        self,
        frame
    ):

        status = (
            self.pupil_calibrator
            .get_status()
        )

        y = 190

        if status["calibrating"]:

            samples = status["samples"]

            duration = status["duration"]

            elapsed = status["elapsed"]

            remaining = max(
                0.0,
                duration - elapsed
            )

            text = (
                f"PUPIL CALIBRATING | "
                f"Samples: {samples} | "
                f"{remaining:.1f}s"
            )

            cv2.putText(
                frame,
                text,
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (0, 255, 255),
                2
            )

        elif status["calibrated"]:

            baseline = status["baseline"]

            text = (
                f"PUPIL CALIBRATED | "
                f"Baseline: {baseline:.4f}"
            )

            cv2.putText(
                frame,
                text,
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (0, 255, 0),
                2
            )

        else:

            cv2.putText(
                frame,
                "PUPIL: RAW / NOT CALIBRATED",
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (0, 165, 255),
                2
            )

    # ========================================================
    # RUN LOCAL CAMERA
    # ========================================================

    def run(self):

        if self.camera is None:

            raise RuntimeError(
                "Camera is disabled. "
                "Use process_frame(frame) "
                "when running in external-frame mode."
            )

        print("\n")
        print("=" * 60)

        print(
            "LIVE EYE + GAZE + PUPIL + EMOTION TRACKING"
        )

        print("=" * 60)

        print(
            "Pupil calibration starts automatically."
        )

        if self.headset_mode:

            print(
                "HEADSET MODE: fixed eye ROIs"
            )

        else:

            print(
                "NORMAL CAMERA MODE: MediaPipe"
            )

        print(
            "Press R = Reset calibration."
        )

        print(
            "Press Q = Quit."
        )

        print("=" * 60)

        fps_timer = time.monotonic()

        fps_frames = 0

        display_fps = 0.0

        while True:

            ret, frame = (
                self.camera.read()
            )

            if not ret:

                print(
                    "Failed to read camera frame."
                )

                break

            try:

                result = (
                    self.process_frame(
                        frame
                    )
                )

                # ------------------------------------------------
                # FPS
                # ------------------------------------------------

                fps_frames += 1

                now = time.monotonic()

                fps_elapsed = (
                    now
                    - fps_timer
                )

                if fps_elapsed >= 1.0:

                    display_fps = (
                        fps_frames
                        / fps_elapsed
                    )

                    fps_frames = 0

                    fps_timer = now

                # ------------------------------------------------
                # STATUS
                # ------------------------------------------------

                if self.headset_mode:

                    cv2.putText(
                        frame,
                        "HEADSET MODE",
                        (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 0),
                        2
                    )

                elif not result.get(
                    "face_detected",
                    False
                ):

                    cv2.putText(
                        frame,
                        "Face: NOT DETECTED",
                        (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2
                    )

                else:

                    cv2.putText(
                        frame,
                        "Face: DETECTED",
                        (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )

                # ------------------------------------------------
                # PERFORMANCE
                # ------------------------------------------------

                processing_time = result.get(
                    "processing_time",
                    0.0
                )

                cv2.putText(
                    frame,
                    (
                        f"FPS: "
                        f"{display_fps:.1f} "
                        f"| Process: "
                        f"{processing_time:.3f}s"
                    ),
                    (20, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2
                )

                # ------------------------------------------------
                # EYES
                # ------------------------------------------------

                self.draw_eye_result(
                    frame,
                    result.get(
                        "left_eye"
                    ),
                    "LEFT EYE"
                )

                self.draw_eye_result(
                    frame,
                    result.get(
                        "right_eye"
                    ),
                    "RIGHT EYE"
                )

                # ------------------------------------------------
                # GAZE
                # ------------------------------------------------

                gaze_x = result.get(
                    "gaze_x"
                )

                gaze_y = result.get(
                    "gaze_y"
                )

                if (
                    gaze_x is not None
                    and gaze_y is not None
                ):

                    cv2.putText(
                        frame,
                        (
                            f"Gaze: "
                            f"{gaze_x:.3f}, "
                            f"{gaze_y:.3f}"
                        ),
                        (20, 95),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (255, 255, 0),
                        2
                    )

                # ------------------------------------------------
                # PUPIL
                # ------------------------------------------------

                raw_pupil = result.get(
                    "pupil_size"
                )

                if raw_pupil is not None:

                    cv2.putText(
                        frame,
                        (
                            f"Pupil raw: "
                            f"{raw_pupil:.5f}"
                        ),
                        (20, 125),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (0, 255, 255),
                        2
                    )

                normalized_pupil = result.get(
                    "normalized_pupil"
                )

                if normalized_pupil is not None:

                    cv2.putText(
                        frame,
                        (
                            f"Pupil norm: "
                            f"{normalized_pupil:.3f}"
                        ),
                        (20, 155),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (0, 255, 255),
                        2
                    )

                # ------------------------------------------------
                # CALIBRATION
                # ------------------------------------------------

                self.draw_calibration_status(
                    frame
                )

                # ------------------------------------------------
                # EMOTION
                # ------------------------------------------------

                emotion_data = result.get(
                    "emotion",
                    {}
                )

                overall_emotion = result.get(
                    "overall_emotion"
                )

                overall_confidence = float(
                    result.get(
                        "overall_confidence",
                        0.0
                    )
                )

                if overall_emotion is not None:

                    text = (
                        f"EMOTION: "
                        f"{overall_emotion} | "
                        f"{overall_confidence:.2f}"
                    )

                else:

                    collected = int(
                        emotion_data.get(
                            "frames_collected",
                            0
                        )
                    )

                    required = int(
                        emotion_data.get(
                            "required_frames",
                            30
                        )
                    )

                    predictions = int(
                        emotion_data.get(
                            "predictions_collected",
                            0
                        )
                    )

                    elapsed = float(
                        emotion_data.get(
                            "elapsed_seconds",
                            0.0
                        )
                    )

                    text = (
                        f"Collecting: "
                        f"{collected}/{required} "
                        f"| Pred: "
                        f"{predictions} "
                        f"| {elapsed:.1f}s"
                    )

                cv2.putText(
                    frame,
                    text,
                    (20, 220),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2
                )

                # ------------------------------------------------
                # POPUP STATUS
                # ------------------------------------------------

                popup = result.get(
                    "popup",
                    {}
                )

                if popup.get(
                    "show_popup",
                    False
                ):

                    cv2.putText(
                        frame,
                        "ADAPTATION AVAILABLE",
                        (20, 255),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (255, 0, 255),
                        2
                    )

                # ------------------------------------------------
                # DISPLAY
                # ------------------------------------------------

                cv2.imshow(
                    "VR Eye Emotion Pipeline",
                    frame
                )

            except Exception as e:

                print(
                    f"Frame processing error: {e}"
                )

            # ----------------------------------------------------
            # KEYBOARD
            # ----------------------------------------------------

            key = (
                cv2.waitKey(1)
                & 0xFF
            )

            if key == ord("q"):

                break

            if key == ord("r"):

                print(
                    "\nResetting pupil calibration..."
                )

                self.pupil_calibrator.reset()

                self.emotion_service.buffer.clear()

                self.emotion_service.window_predictions.clear()

                self.emotion_service.window_start = None

                self.auto_calibration_started = False

                self.last_overall_emotion = None

                self.last_overall_confidence = 0.0

                self.last_overall_predictions = 0

                self.popup_emotion_consumed = False

                self.popup_emotion = None

                self.popup_confidence = 0.0

                self.start_pupil_calibration()

        self.release()

    # ========================================================
    # RELEASE
    # ========================================================

    def release(self):

        if self.camera is not None:

            try:

                self.camera.release()

            except Exception:

                pass

            self.camera = None

        if self.face_landmarker is not None:

            try:

                self.face_landmarker.close()

            except Exception:

                pass

            self.face_landmarker = None

        cv2.destroyAllWindows()

        if self.processing_times:

            avg_time = float(
                np.mean(
                    self.processing_times
                )
            )

            print(
                f"\nAverage recent "
                f"processing time: "
                f"{avg_time:.3f}s"
            )

            print(
                f"Approx processing FPS: "
                f"{1.0 / max(avg_time, 1e-6):.2f}"
            )

        status = (
            self.pupil_calibrator
            .get_status()
        )

        if status["calibrated"]:

            print(
                f"Pupil calibration: "
                f"completed "
                f"(baseline="
                f"{status['baseline']:.6f})"
            )

        else:

            print(
                "Pupil calibration: "
                "not completed."
            )

        print(
            "Pipeline stopped."
        )


# ============================================================
# LOCAL CAMERA TEST
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # NORMAL WEBCAM TEST
    # ========================================================
    #
    # For current normal webcam testing:
    #
    # pipeline = LiveEmotionPipeline(
    #     camera_index=0,
    #     headset_mode=False
    # )
    #
    # ========================================================

    # ========================================================
    # HEADSET OV9281 TEST
    # ========================================================
    #
    # Once OV9281 is connected:
    #
    # 1. Find the correct camera index.
    # 2. Confirm the actual frame.
    # 3. Adjust HEADSET_EYE_ROIS if necessary.
    #
    # ========================================================

    pipeline = LiveEmotionPipeline(
        camera_index=0,
        headset_mode=True
    )

    try:

        pipeline.run()

    except KeyboardInterrupt:

        pipeline.release()

    except Exception as e:

        pipeline.release()

        print(
            "\nPipeline failed:"
        )

        print(e)