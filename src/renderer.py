import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def render_video(
    manim_file: str,
    scene_name: str,
    quality: str = "l"
) -> str:
    """
    Render a Manim scene safely from a temporary directory.

    This prevents Uvicorn --reload from detecting changes
    in generated_scene.py and restarting the FastAPI server.

    quality:
        l = 480p15
        m = 720p30
        h = 1080p30
    """

    original_file = Path(manim_file).resolve()

    if not original_file.exists():
        raise FileNotFoundError(
            f"Manim file not found: {original_file}"
        )

    print("\n" + "=" * 60)
    print("MANIM VIDEO RENDERER")
    print("=" * 60)

    print(f"Project root : {BASE_DIR}")
    print(f"Original file: {original_file}")
    print(f"Scene        : {scene_name}")
    print(f"Quality      : {quality}")
    print(f"Python       : {sys.executable}")

    # ---------------------------------------------------------
    # CHECK MANIM
    # ---------------------------------------------------------

    try:
        version_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "manim",
                "--version"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        print("\nManim version:")
        print(version_result.stdout)

    except Exception as e:
        raise RuntimeError(
            f"Could not check Manim installation: {e}"
        )

    # ---------------------------------------------------------
    # TEMP DIRECTORY
    # ---------------------------------------------------------
    #
    # IMPORTANT:
    # Do NOT render directly from Adaptive-learning-LLM/
    # because Uvicorn --reload watches generated_scene.py.
    #
    # We create a completely separate temporary directory.
    #

    temp_root = Path(
        tempfile.mkdtemp(
            prefix="adaptive_manim_"
        )
    )

    print(f"Temporary render directory: {temp_root}")

    try:

        # -----------------------------------------------------
        # COPY GENERATED SCENE
        # -----------------------------------------------------

        temp_scene = (
            temp_root /
            original_file.name
        )

        shutil.copy2(
            original_file,
            temp_scene
        )

        print(
            f"Copied scene to:\n{temp_scene}"
        )

        # -----------------------------------------------------
        # MEDIA DIRECTORY
        # -----------------------------------------------------

        media_dir = (
            temp_root /
            "media"
        )

        media_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # -----------------------------------------------------
        # MANIM COMMAND
        # -----------------------------------------------------

        command = [
            sys.executable,
            "-m",
            "manim",

            # Quality
            f"-q{quality}",

            # Verbose output
            "-v",
            "INFO",

            # Scene file
            str(temp_scene),

            # Scene name
            scene_name,

            # Output filename
            "-o",
            "generated_video",

            # Put all Manim generated files
            # outside the project directory
            "--media_dir",
            str(media_dir)
        ]

        print("\n" + "=" * 60)
        print("RUNNING MANIM")
        print("=" * 60)

        print(
            " ".join(
                f'"{arg}"' if " " in str(arg) else str(arg)
                for arg in command
            )
        )

        # -----------------------------------------------------
        # RUN MANIM
        # -----------------------------------------------------

        result = subprocess.run(
            command,
            cwd=str(temp_root),
            capture_output=True,
            text=True
        )

        # -----------------------------------------------------
        # OUTPUT
        # -----------------------------------------------------

        print("\n===== MANIM STDOUT =====")
        print(result.stdout)

        if result.stderr:
            print("\n===== MANIM STDERR =====")
            print(result.stderr)

        # -----------------------------------------------------
        # FAILURE
        # -----------------------------------------------------

        if result.returncode != 0:

            raise RuntimeError(
                "Manim rendering failed.\n\n"
                f"Exit code: {result.returncode}\n\n"
                f"STDOUT:\n{result.stdout}\n\n"
                f"STDERR:\n{result.stderr}"
            )

        # -----------------------------------------------------
        # FIND VIDEO
        # -----------------------------------------------------

        video_candidates = list(
            media_dir.rglob(
                "generated_video.mp4"
            )
        )

        if not video_candidates:

            # Debug: show what Manim actually generated
            generated_files = [
                str(p)
                for p in media_dir.rglob("*")
                if p.is_file()
            ]

            raise FileNotFoundError(
                "Manim finished successfully, "
                "but generated_video.mp4 was not found.\n\n"
                f"Media directory:\n{media_dir}\n\n"
                f"Generated files:\n"
                + "\n".join(generated_files)
            )

        rendered_video = video_candidates[0].resolve()

        # -----------------------------------------------------
        # COPY FINAL VIDEO TO PROJECT OUTPUT
        # -----------------------------------------------------

        output_dir = (
            BASE_DIR /
            "media" /
            "generated_videos"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        final_video = (
            output_dir /
            "generated_video.mp4"
        )

        shutil.copy2(
            rendered_video,
            final_video
        )

        print("\n" + "=" * 60)
        print("VIDEO RENDERED SUCCESSFULLY")
        print("=" * 60)

        print(
            f"Temporary video:\n{rendered_video}"
        )

        print(
            f"Final video:\n{final_video}"
        )

        return str(final_video)

    finally:

        # -----------------------------------------------------
        # CLEAN TEMP DIRECTORY
        # -----------------------------------------------------

        try:
            shutil.rmtree(
                temp_root,
                ignore_errors=True
            )

            print(
                f"\nTemporary directory cleaned:\n{temp_root}"
            )

        except Exception as e:

            print(
                f"Warning: could not clean temp directory: {e}"
            )


# =============================================================
# DIRECT TEST
# =============================================================

if __name__ == "__main__":

    video = render_video(
        manim_file=str(
            BASE_DIR /
            "generated_scene.py"
        ),
        scene_name="GeneratedScene",
        quality="l"
    )

    print(
        f"\nFinal rendered video path:\n{video}"
    )