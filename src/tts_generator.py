import asyncio
from pathlib import Path

import edge_tts


BASE_DIR = Path(__file__).resolve().parent.parent.parent

OUTPUT_DIR = BASE_DIR / "generated_audio"

VOICE = "en-US-AriaNeural"
RATE = "+0%"


async def generate_audio(
    text: str,
    output_path: str
):
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE
    )

    await communicate.save(output_path)


async def generate_scene_audios(
    scene_json: dict
):
    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    audio_files = []

    if "scenes" not in scene_json:
        raise ValueError(
            "Invalid scene JSON: scenes missing"
        )

    for scene in scene_json["scenes"]:

        scene_id = scene["scene_id"]

        narration = scene.get(
            "narration",
            ""
        )

        if not narration:
            continue

        output_file = OUTPUT_DIR / (
            f"scene_{scene_id}.mp3"
        )

        await generate_audio(
            narration,
            str(output_file)
        )

        audio_files.append(
            str(output_file)
        )

        print(
            f"Generated audio: {output_file}"
        )

    if not audio_files:
        raise ValueError(
            "No narration found in scene JSON."
        )

    return audio_files


def create_audio(
    scene_json: dict
):
    return asyncio.run(
        generate_scene_audios(
            scene_json
        )
    )


if __name__ == "__main__":

    sample_json = {
        "video_title": "Stack",

        "scenes": [
            {
                "scene_id": 1,
                "narration": (
                    "A stack follows the "
                    "Last In First Out principle."
                )
            },
            {
                "scene_id": 2,
                "narration": (
                    "The last element inserted "
                    "into the stack is removed first."
                )
            }
        ]
    }

    files = create_audio(
        sample_json
    )

    print("\nGenerated files:")

    for file in files:
        print(file)