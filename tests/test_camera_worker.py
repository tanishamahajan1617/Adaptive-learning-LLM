from src.routes.emotion_routes import pipeline
from src.services.camera_worker import CameraWorker

import time


worker = CameraWorker(
    pipeline=pipeline,
    camera_index=3,
    fps=10
)

worker.start()

try:

    while True:
        time.sleep(1)

except KeyboardInterrupt:

    worker.stop()