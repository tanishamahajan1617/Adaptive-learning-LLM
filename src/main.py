from fastapi import FastAPI
from src.routes.video_routes import router as video_router
from src.routes.emotion_routes import router as emotion_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_router)

app.include_router(emotion_router)