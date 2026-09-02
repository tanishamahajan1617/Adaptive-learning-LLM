from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.schemas.video_schema import VideoRequest
from src.services.video_service import VideoService
from src.routes.emotion_routes import pipeline


router = APIRouter(
    prefix="/video",
    tags=["Video"]
)


@router.post("/generate")
def generate_video(request: VideoRequest):

    try:

        # ============================================
        # GET LATEST EMOTION FROM EMOTION PIPELINE
        # ============================================

        emotion = pipeline.last_overall_emotion
        confidence = pipeline.last_overall_confidence

        # If emotion is not available yet
        # use Neutral by default
        if emotion is None:
            emotion = "Neutral"
            confidence = 1.0


        # ============================================
        # LOG REQUEST
        # ============================================

        print("\n" + "=" * 60)
        print("VIDEO GENERATION REQUEST")
        print("=" * 60)

        print(f"Query: {request.query}")
        print(f"Emotion: {emotion}")
        print(f"Emotion confidence: {confidence:.4f}")

        print("=" * 60)


        # ============================================
        # GENERATE VIDEO
        # ============================================

        video_path = VideoService.generate_video(
            query=request.query,
            emotion=emotion
        )


        # ============================================
        # RETURN VIDEO
        # ============================================

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