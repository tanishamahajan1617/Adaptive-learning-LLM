from pydantic import BaseModel, Field


class VideoRequest(BaseModel):
    query: str = Field(..., min_length=1)