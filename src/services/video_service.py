from pathlib import Path

from src.retrieval import retrieve
from src.script_generator import generate_video_script
from src.manim_generator import (
    generate_manim_code,
    clean_manim_code,
    save_manim_file
)
from src.renderer import render_video
from src.tts_generator import create_audio
from src.merger.video_audio_merger import create_final_video


BASE_DIR = Path(__file__).resolve().parent.parent.parent

MANIM_FILE = BASE_DIR / "generated_scene.py"


class VideoService:

    @staticmethod
    def generate_video(
        query: str,
        emotion: str
    ):

        # -----------------------------------------
        # 1. RETRIEVE KNOWLEDGE
        # -----------------------------------------

        print("\n[1/6] Retrieving knowledge...")

        retrieved_chunks = retrieve(query)


        # -----------------------------------------
        # 2. GENERATE SCENE JSON
        # -----------------------------------------

        print("\n[2/6] Generating scene plan...")

        scene_json = generate_video_script(
            query=query,
            retrieved_chunks=retrieved_chunks,
            emotion={
                "state": emotion
            }
        )


        # -----------------------------------------
        # 3. GENERATE MANIM CODE
        # -----------------------------------------

        print("\n[3/6] Generating Manim code...")

        manim_code = generate_manim_code(
            scene_json
        )

        manim_code = clean_manim_code(
            manim_code
        )

        save_manim_file(
            manim_code,
            str(MANIM_FILE)
        )

        print(
            f"Generated Manim file: {MANIM_FILE}"
        )


        # -----------------------------------------
        # 4. RENDER MANIM VIDEO
        # -----------------------------------------

        print("\n[4/6] Rendering video...")

        video_path = render_video(
            manim_file=str(MANIM_FILE),
            scene_name="GeneratedScene",
            quality="l"
        )

        print(
            f"Video rendered: {video_path}"
        )


        # -----------------------------------------
        # 5. GENERATE TTS AUDIO
        # -----------------------------------------

        print("\n[5/6] Generating narration...")

        audio_files = create_audio(scene_json)


        print(
            f"Generated {len(audio_files)} audio files."
        )


        # -----------------------------------------
        # 6. MERGE VIDEO + AUDIO
        # -----------------------------------------

        print("\n[6/6] Merging video and audio...")

        final_video = create_final_video(
            video_path=video_path,
            audio_files=audio_files
        )

        print(
            f"\nFINAL VIDEO: {final_video}"
        )

        return final_video