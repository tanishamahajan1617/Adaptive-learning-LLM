from pydantic import BaseModel


class EmotionFrameResponse(BaseModel):
    status: str
    session_id: str