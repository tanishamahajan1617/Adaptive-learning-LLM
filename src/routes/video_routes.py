import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.schemas.video_schema import VideoRequest
from src.services.video_service import VideoService
from src.services.emotion_state import EmotionState


router = APIRouter(
    prefix="/video",
    tags=["Video"]
)


@router.post("/generate")
def generate_video(request: VideoRequest):

    try:

        # =====================================================
        # WAIT FOR REAL EMOTION
        # =====================================================

        timeout = 15.0
        poll_interval = 0.25
        start_time = time.time()

        while True:

            state = EmotionState.get()

            emotion = state["emotion"]
            confidence = float(state["confidence"])
            predictions_used = int(state["predictions"])

            # Real overall emotion is available
            if emotion is not None and predictions_used > 0:
                break

            # Safety timeout
            if time.time() - start_time >= timeout:

                print("Emotion prediction not ready within timeout.")
                print("Using Neutral as fallback.")

                emotion = "Neutral"
                confidence = 0.0
                predictions_used = 0

                break

            time.sleep(poll_interval)

        # =====================================================
        # IMMUTABLE EMOTION SNAPSHOT
        # =====================================================

        emotion_snapshot = emotion
        confidence_snapshot = confidence
        predictions_snapshot = predictions_used

        print("\n" + "=" * 60)
        print("VIDEO GENERATION REQUEST")
        print("=" * 60)
        print(f"Query: {request.query}")
        print(f"Emotion: {emotion_snapshot}")
        print(f"Emotion confidence: {confidence_snapshot:.4f}")
        print(f"Predictions used: {predictions_snapshot}")
        print("=" * 60)

        # =====================================================
        # GENERATE VIDEO
        # =====================================================

        video_path = VideoService.generate_video(
            query=request.query,
            emotion=emotion_snapshot
        )

        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename="adaptive_learning_video.mp4"
        )

    except HTTPException:
        raise

    except Exception as e:

        print(f"Video generation error: {e}")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )