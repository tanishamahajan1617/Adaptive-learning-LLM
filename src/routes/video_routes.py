from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.schemas.video_schema import VideoRequest
from src.services.video_service import VideoService
from src.services.emotion_state import EmotionState


router = APIRouter(
    prefix="/video",
    tags=["Video"]
)


# ============================================================
# GENERATE ADAPTIVE VIDEO
# ============================================================

@router.post("/generate")
def generate_video(request: VideoRequest):

    try:

        # ====================================================
        # GET EMOTION SNAPSHOT
        # ====================================================

        state = EmotionState.get()

        emotion = state["emotion"]
        confidence = float(
            state["confidence"]
        )

        predictions_used = int(
            state["predictions"]
        )

        # ----------------------------------------------------
        # DEFAULT LEARNER STATE
        # ----------------------------------------------------

        # Before the first overall model prediction,
        # the learner is treated as Neutral.
        #
        # Confidence remains 0 because there is no
        # actual model prediction yet.

        if emotion is None:

            emotion = "Neutral"
            confidence = 0.0
            predictions_used = 0

        # ====================================================
        # CREATE IMMUTABLE SNAPSHOT
        # ====================================================

        # From this point onward, this video-generation
        # request uses this emotion value even if the
        # live camera predicts another emotion while the
        # video is being generated.

        emotion_snapshot = emotion
        confidence_snapshot = confidence

        # ====================================================
        # LOG REQUEST
        # ====================================================

        print("\n" + "=" * 60)
        print("VIDEO GENERATION REQUEST")
        print("=" * 60)

        print(
            f"Query: {request.query}"
        )

        print(
            f"Emotion: {emotion_snapshot}"
        )

        print(
            f"Emotion confidence: "
            f"{confidence_snapshot:.4f}"
        )

        print(
            f"Predictions used: "
            f"{predictions_used}"
        )

        print("=" * 60)

        # ====================================================
        # GENERATE VIDEO
        # ====================================================

        video_path = VideoService.generate_video(
            query=request.query,
            emotion=emotion_snapshot
        )

        # ====================================================
        # RETURN VIDEO
        # ====================================================

        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename="adaptive_learning_video.mp4"
        )

    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:

        raise

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as e:

        print(
            f"Video generation error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )