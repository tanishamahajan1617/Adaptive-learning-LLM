from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.video_routes import router as video_router
from src.routes.emotion_routes import router as emotion_router
from src.services.camera_worker import CameraWorker


# ============================================================
# Camera Worker
# ============================================================

camera_worker = None


@asynccontextmanager
async def lifespan(app: FastAPI):

    global camera_worker

    # --------------------------------------------------------
    # FastAPI startup
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("STARTING APPLICATION")
    print("=" * 60)

    # Import the SAME pipeline used by emotion_routes
    from src.routes.emotion_routes import pipeline

    camera_worker = CameraWorker(
        pipeline=pipeline,
        camera_index=2,
        fps=10
    )

    camera_worker.start()

    print("FastAPI startup complete.")
    print("=" * 60 + "\n")

    yield

    # --------------------------------------------------------
    # FastAPI shutdown
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("SHUTTING DOWN APPLICATION")
    print("=" * 60)

    if camera_worker is not None:
        camera_worker.stop()

    print("FastAPI shutdown complete.")
    print("=" * 60)


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    lifespan=lifespan
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Routes
# ============================================================

app.include_router(video_router)
app.include_router(emotion_router)