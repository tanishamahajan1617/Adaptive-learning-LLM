import cv2
import threading
import time


class CameraWorker:

    def __init__(
        self,
        pipeline,
        camera_index=3,
        fps=15
    ):
        self.pipeline = pipeline
        self.camera_index = camera_index
        self.fps = fps

        self.camera = None
        self.thread = None

        self.running = False

    # ========================================================
    # START
    # ========================================================

    def start(self):

        if self.running:
            print("Camera worker is already running.")
            return

        print(
            f"\nStarting OV9281 camera worker "
            f"(Camera {self.camera_index})..."
        )

        self.camera = cv2.VideoCapture(
            self.camera_index
        )

        if not self.camera.isOpened():

            print(
                f"❌ Could not open Camera "
                f"{self.camera_index}"
            )

            self.camera.release()
            self.camera = None

            return

        # ----------------------------------------------------
        # Camera configuration
        # ----------------------------------------------------

        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

        self.camera.set(
            cv2.CAP_PROP_FPS,
            self.fps
        )

        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

        print(
            f"✅ Camera worker started "
            f"on Camera {self.camera_index}"
        )

    # ========================================================
    # BACKGROUND LOOP
    # ========================================================

    def _run(self):

        frame_interval = 1.0 / self.fps

        while self.running:

            start_time = time.time()

            try:

                ret, frame = (
                    self.camera.read()
                )

                if not ret:

                    print(
                        "❌ Failed to read "
                        "camera frame"
                    )

                    time.sleep(0.1)
                    continue

                # ------------------------------------------------
                # Send frame to emotion pipeline
                # ------------------------------------------------

                self.pipeline.process_frame(
                    frame
                )

            except Exception as e:

                print(
                    f"Camera processing error: {e}"
                )

            # ----------------------------------------------------
            # Maintain approximate FPS
            # ----------------------------------------------------

            elapsed = (
                time.time() - start_time
            )

            sleep_time = (
                frame_interval - elapsed
            )

            if sleep_time > 0:
                time.sleep(sleep_time)

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        if not self.running:
            return

        print(
            "\nStopping camera worker..."
        )

        self.running = False

        if self.thread is not None:

            self.thread.join(
                timeout=2.0
            )

            self.thread = None

        if self.camera is not None:

            self.camera.release()
            self.camera = None

        print(
            "Camera worker stopped."
        )