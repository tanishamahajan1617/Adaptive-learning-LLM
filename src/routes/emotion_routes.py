from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2

from src.services.live_emotion_pipeline import LiveEmotionPipeline


router = APIRouter(
    prefix="/emotion",
    tags=["Emotion"]
)


# ============================================================
# SHARED PIPELINE INSTANCE
# ============================================================

pipeline = LiveEmotionPipeline(
    camera_index=None,
    headset_mode=True
)


# ============================================================
# PROCESS EMOTION FRAME
# ============================================================

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
        # EXTRACT EMOTION
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

            # -----------------------------------------------
            # CURRENT / OVERALL EMOTION
            # -----------------------------------------------

            "emotion": overall_emotion,

            "confidence": overall_confidence,

            "predictions_used": int(
                result.get(
                    "emotion",
                    {}
                ).get(
                    "predictions_used",
                    0
                )
            ),

            "overall_ready": bool(
                emotion_data.get(
                    "overall_ready",
                    False
                )
            ),


            # -----------------------------------------------
            # POPUP
            # -----------------------------------------------

            "show_popup": bool(
                popup.get(
                    "show_popup",
                    False
                )
            ),

            "adaptation": popup.get(
                "adaptation"
            ),

            "popup_message": popup.get(
                "message"
            ),


            # -----------------------------------------------
            # CALIBRATION
            # -----------------------------------------------

            "calibration": result.get(
                "calibration"
            ),


            # -----------------------------------------------
            # DETECTION
            # -----------------------------------------------

            "face_detected": result.get(
                "face_detected",
                False
            ),

            "eyes_detected": result.get(
                "eyes_detected",
                False
            ),


            # -----------------------------------------------
            # OPTIONAL DEBUG FEATURES
            # -----------------------------------------------

            "gaze_x": result.get(
                "gaze_x"
            ),

            "gaze_y": result.get(
                "gaze_y"
            ),

            "pupil_size": result.get(
                "pupil_size"
            ),

            "normalized_pupil": result.get(
                "normalized_pupil"
            ),

            "processing_time": result.get(
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

@router.get("/current")
async def get_current_emotion():
        return {
            "success": True,
            "emotion": pipeline.last_overall_emotion or "Neutral",
            "confidence": pipeline.last_overall_confidence or 1.0,
        }