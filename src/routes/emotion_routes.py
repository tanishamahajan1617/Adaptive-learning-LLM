from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2

from src.services.live_emotion_pipeline import LiveEmotionPipeline
from src.services.emotion_state import EmotionState


router = APIRouter(
    prefix="/emotion",
    tags=["Emotion"]
)


# ============================================================
# SHARED PIPELINE INSTANCE
# ============================================================

# Camera is NOT opened here.
# CameraWorker owns OV9281 Camera 3 and continuously sends
# frames to this pipeline.
pipeline = LiveEmotionPipeline(
    camera_index=None,
    headset_mode=True
)


# ============================================================
# PROCESS EMOTION FRAME
# ============================================================

# This endpoint is kept for:
# - manual testing
# - debugging
# - sending a single image
#
# Normal production flow uses CameraWorker instead.

@router.post("/frame")
async def process_frame(
    file: UploadFile = File(...)
):

    try:

        # ----------------------------------------------------
        # READ UPLOADED IMAGE
        # ----------------------------------------------------

        contents = await file.read()

        if not contents:

            raise HTTPException(
                status_code=400,
                detail="Empty image received."
            )

        # ----------------------------------------------------
        # BYTES -> NUMPY
        # ----------------------------------------------------

        np_array = np.frombuffer(
            contents,
            np.uint8
        )

        # ----------------------------------------------------
        # NUMPY -> OPENCV IMAGE
        # ----------------------------------------------------

        frame = cv2.imdecode(
            np_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:

            raise HTTPException(
                status_code=400,
                detail="Could not decode image."
            )

        # ----------------------------------------------------
        # PROCESS FRAME
        # ----------------------------------------------------

        result = pipeline.process_frame(
            frame
        )

        # ----------------------------------------------------
        # EXTRACT CURRENT RESULT
        # ----------------------------------------------------

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

        predictions_used = int(
            emotion_data.get(
                "predictions_used",
                0
            )
        )

        overall_ready = bool(
            emotion_data.get(
                "overall_ready",
                False
            )
        )

        # ----------------------------------------------------
        # POPUP
        # ----------------------------------------------------

        popup = result.get(
            "popup",
            {}
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "success": True,

            # =================================================
            # EMOTION
            # =================================================

            "emotion":
                overall_emotion,

            "confidence":
                overall_confidence,

            "predictions_used":
                predictions_used,

            "overall_ready":
                overall_ready,

            # =================================================
            # POPUP
            # =================================================

            "show_popup":
                bool(
                    popup.get(
                        "show_popup",
                        False
                    )
                ),

            "adaptation":
                popup.get(
                    "adaptation"
                ),

            "popup_message":
                popup.get(
                    "message"
                ),

            # =================================================
            # CALIBRATION
            # =================================================

            "calibration":
                result.get(
                    "calibration"
                ),

            # =================================================
            # DETECTION
            # =================================================

            "face_detected":
                result.get(
                    "face_detected",
                    False
                ),

            "eyes_detected":
                result.get(
                    "eyes_detected",
                    False
                ),

            # =================================================
            # DEBUG FEATURES
            # =================================================

            "gaze_x":
                result.get(
                    "gaze_x"
                ),

            "gaze_y":
                result.get(
                    "gaze_y"
                ),

            "pupil_size":
                result.get(
                    "pupil_size"
                ),

            "normalized_pupil":
                result.get(
                    "normalized_pupil"
                ),

            "processing_time":
                result.get(
                    "processing_time"
                )
        }

    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:

        raise

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# POPUP ACKNOWLEDGEMENT
# ============================================================

@router.post("/popup/acknowledge")
async def acknowledge_popup():

    try:

        result = pipeline.acknowledge_popup()

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# CURRENT EMOTION + ADAPTATION STATE
# ============================================================

# Unity should use THIS endpoint.
#
# It does NOT process a camera frame.
# It only reads the latest state produced by the
# background CameraWorker.

@router.get("/current")
async def get_current_emotion():

    # --------------------------------------------------------
    # READ LATEST SHARED EMOTION
    # --------------------------------------------------------

    state = EmotionState.get()

    emotion = state["emotion"]
    confidence = float(
        state["confidence"]
    )

    predictions_used = int(
        state["predictions"]
    )

    # --------------------------------------------------------
    # DEFAULT STATE
    # --------------------------------------------------------

    # At application startup, before the first actual
    # overall prediction, the learner is considered Neutral.
    #
    # Confidence remains 0.0 because the model has not
    # produced a prediction yet.

    if emotion is None:

        emotion = "Neutral"

        confidence = 0.0

        predictions_used = 0

    # --------------------------------------------------------
    # POPUP / ADAPTATION
    # --------------------------------------------------------

    popup_state = pipeline.get_popup_state()

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "success": True,

        # ====================================================
        # CURRENT EMOTION
        # ====================================================

        "emotion":
            emotion,

        "confidence":
            confidence,

        "predictions_used":
            predictions_used,

        # ====================================================
        # POPUP
        # ====================================================

        "show_popup":
            bool(
                popup_state.get(
                    "show_popup",
                    False
                )
            ),

        "adaptation":
            popup_state.get(
                "adaptation"
            ),

        "popup_message":
            popup_state.get(
                "message"
            )
    }