
import asyncio
import json
import math
import subprocess
from pathlib import Path

import edge_tts


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

OUTPUT_DIR = BASE_DIR / "generated_audio"


# ============================================================
# TTS CONFIG
# ============================================================

VOICE = "en-US-AriaNeural"
RATE = "+0%"


# ============================================================
# AUDIO GENERATION
# ============================================================

async def generate_audio(
    text: str,
    output_path: str
):
    """
    Generate narration audio using Edge TTS.
    """

    if not text or not text.strip():
        raise ValueError(
            "Cannot generate audio from empty narration."
        )

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE
    )

    await communicate.save(
        output_path
    )


# ============================================================
# AUDIO DURATION
# ============================================================

def get_audio_duration(
    audio_path: str
) -> float:
    """
    Get actual audio duration using ffprobe.
    """

    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        duration = float(
            result.stdout.strip()
        )

    except FileNotFoundError as e:

        raise RuntimeError(
            "ffprobe was not found. "
            "Make sure FFmpeg is installed "
            "and added to PATH."
        ) from e

    except (
        subprocess.CalledProcessError,
        ValueError
    ) as e:

        raise RuntimeError(
            f"Could not determine audio duration for: "
            f"{audio_path}"
        ) from e

    if not math.isfinite(duration) or duration <= 0:

        raise RuntimeError(
            f"Invalid audio duration: {duration}"
        )

    return duration


# ============================================================
# VALIDATE BEAT RATIOS
# ============================================================

def validate_beat_ratios(
    scene: dict
):
    """
    Validate normalized beat timing before converting
    ratios into actual seconds.
    """

    beats = scene.get(
        "teaching_beats",
        []
    )

    if not beats:
        raise ValueError(
            f"Scene {scene.get('scene_id')} "
            "contains no teaching beats."
        )

    previous_sequence = 0
    previous_end_ratio = 0.0

    for index, beat in enumerate(beats):

        beat_name = (
            f"Scene {scene.get('scene_id')}, "
            f"Beat {index + 1}"
        )

        # ----------------------------------------------------
        # Required timing fields
        # ----------------------------------------------------

        if "start_ratio" not in beat:
            raise ValueError(
                f"{beat_name}: missing start_ratio."
            )

        if "end_ratio" not in beat:
            raise ValueError(
                f"{beat_name}: missing end_ratio."
            )

        # ----------------------------------------------------
        # Convert to float
        # ----------------------------------------------------

        try:

            start_ratio = float(
                beat["start_ratio"]
            )

            end_ratio = float(
                beat["end_ratio"]
            )

        except (
            TypeError,
            ValueError
        ) as e:

            raise ValueError(
                f"{beat_name}: start_ratio and "
                "end_ratio must be numeric."
            ) from e

        # ----------------------------------------------------
        # Range
        # ----------------------------------------------------

        if not (
            0.0 <= start_ratio <= 1.0
            and
            0.0 <= end_ratio <= 1.0
        ):

            raise ValueError(
                f"{beat_name}: timing ratios "
                "must be between 0 and 1."
            )

        # ----------------------------------------------------
        # Valid interval
        # ----------------------------------------------------

        if start_ratio >= end_ratio:

            raise ValueError(
                f"{beat_name}: "
                "start_ratio must be smaller "
                "than end_ratio."
            )

        # ----------------------------------------------------
        # Sequence
        # ----------------------------------------------------

        try:

            sequence = int(
                beat["sequence"]
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ) as e:

            raise ValueError(
                f"{beat_name}: invalid sequence."
            ) from e

        if sequence <= previous_sequence:

            raise ValueError(
                f"{beat_name}: sequence must be "
                "strictly increasing."
            )

        previous_sequence = sequence

        # ----------------------------------------------------
        # No gaps / overlaps
        # ----------------------------------------------------

        if not math.isclose(
            start_ratio,
            previous_end_ratio,
            abs_tol=1e-6
        ):

            raise ValueError(
                f"{beat_name}: timing gap or overlap "
                f"detected. Expected start_ratio "
                f"{previous_end_ratio}, got "
                f"{start_ratio}."
            )

        previous_end_ratio = end_ratio

        # Store normalized values
        beat["start_ratio"] = start_ratio
        beat["end_ratio"] = end_ratio

    # ========================================================
    # Full scene coverage
    # ========================================================

    first_start = float(
        beats[0]["start_ratio"]
    )

    last_end = float(
        beats[-1]["end_ratio"]
    )

    if not math.isclose(
        first_start,
        0.0,
        abs_tol=1e-6
    ):

        raise ValueError(
            f"Scene {scene.get('scene_id')}: "
            "first beat must start at 0.0."
        )

    if not math.isclose(
        last_end,
        1.0,
        abs_tol=1e-6
    ):

        raise ValueError(
            f"Scene {scene.get('scene_id')}: "
            "last beat must end at 1.0."
        )


# ============================================================
# APPLY ACTUAL AUDIO TIMING
# ============================================================

def apply_audio_timing(
    scene: dict,
    audio_duration: float
):
    """
    Convert normalized beat ratios into actual seconds.

    Example:

        audio_duration = 8.42
        start_ratio = 0.25

        start_time = 2.105 seconds
    """

    if audio_duration <= 0:

        raise ValueError(
            "Audio duration must be greater than zero."
        )

    beats = scene.get(
        "teaching_beats",
        []
    )

    if not beats:

        raise ValueError(
            f"Scene {scene.get('scene_id')} "
            "contains no teaching beats."
        )

    # --------------------------------------------------------
    # Validate ratios first
    # --------------------------------------------------------

    validate_beat_ratios(
        scene
    )

    # --------------------------------------------------------
    # Store actual scene duration
    # --------------------------------------------------------

    scene["audio_duration"] = round(
        audio_duration,
        3
    )

    scene["duration"] = round(
        audio_duration,
        3
    )

    # --------------------------------------------------------
    # Convert ratios → seconds
    # --------------------------------------------------------

    for beat in beats:

        start_ratio = beat["start_ratio"]
        end_ratio = beat["end_ratio"]

        start_time = (
            start_ratio
            * audio_duration
        )

        end_time = (
            end_ratio
            * audio_duration
        )

        beat_duration = (
            end_time
            - start_time
        )

        beat["start_time"] = round(
            start_time,
            3
        )

        beat["end_time"] = round(
            end_time,
            3
        )

        beat["duration"] = round(
            beat_duration,
            3
        )

    # --------------------------------------------------------
    # Force exact boundaries after rounding
    # --------------------------------------------------------

    beats[0]["start_time"] = 0.0

    beats[-1]["end_time"] = round(
        audio_duration,
        3
    )

    # Recalculate durations after boundary correction
    for index, beat in enumerate(beats):

        beat["duration"] = round(
            beat["end_time"]
            - beat["start_time"],
            3
        )


# ============================================================
# GENERATE SCENE AUDIOS
# ============================================================

async def generate_scene_audios(
    scene_json: dict
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if "scenes" not in scene_json:

        raise ValueError(
            "Invalid scene JSON: scenes missing."
        )

    if not isinstance(
        scene_json["scenes"],
        list
    ):

        raise ValueError(
            "Invalid scene JSON: scenes must be a list."
        )

    audio_files = []

    for scene in scene_json["scenes"]:

        scene_id = scene.get(
            "scene_id"
        )

        if scene_id is None:

            raise ValueError(
                "Scene is missing scene_id."
            )

        narration = scene.get(
            "narration",
            ""
        ).strip()

        if not narration:

            print(
                f"Skipping scene {scene_id}: "
                "no narration."
            )

            continue

        output_file = (
            OUTPUT_DIR
            / f"scene_{scene_id}.mp3"
        )

        # ----------------------------------------------------
        # Generate TTS
        # ----------------------------------------------------

        await generate_audio(
            narration,
            str(output_file)
        )

        # ----------------------------------------------------
        # Measure actual duration
        # ----------------------------------------------------

        audio_duration = get_audio_duration(
            str(output_file)
        )

        # ----------------------------------------------------
        # Apply timing
        # ----------------------------------------------------

        apply_audio_timing(
            scene,
            audio_duration
        )

        audio_files.append(
            str(output_file)
        )

        print(
            f"\nGenerated audio: {output_file}"
        )

        print(
            f"Scene {scene_id} duration: "
            f"{audio_duration:.3f}s"
        )

        print(
            "Beat timings:"
        )

        for beat in scene.get(
            "teaching_beats",
            []
        ):

            print(
                f"  {beat['beat_id']}: "
                f"{beat['start_time']:.3f}s → "
                f"{beat['end_time']:.3f}s "
                f"({beat['duration']:.3f}s)"
            )

    if not audio_files:

        raise ValueError(
            "No narration found in scene JSON."
        )

    return audio_files


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def create_audio(
    scene_json: dict
):

    return asyncio.run(
        generate_scene_audios(
            scene_json
        )
    )


# ============================================================
# SAVE TIMED SCENE JSON
# ============================================================

def save_timed_scene_json(
    scene_json: dict,
    output_path: str
):

    output_file = Path(
        output_path
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            scene_json,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"\nTimed scene JSON saved: "
        f"{output_file}"
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    sample_json = {

        "video_title": "Stack",

        "scenes": [

            {
                "scene_id": 1,

                "narration": (
                    "A stack follows the "
                    "Last In First Out principle."
                ),

                "duration": 5,

                "teaching_beats": [

                    {
                        "beat_id": "scene_1_beat_1",
                        "sequence": 1,
                        "start_ratio": 0.0,
                        "end_ratio": 0.5
                    },

                    {
                        "beat_id": "scene_1_beat_2",
                        "sequence": 2,
                        "start_ratio": 0.5,
                        "end_ratio": 1.0
                    }
                ]
            },

            {
                "scene_id": 2,

                "narration": (
                    "The last element inserted "
                    "into the stack is removed first."
                ),

                "duration": 5,

                "teaching_beats": [

                    {
                        "beat_id": "scene_2_beat_1",
                        "sequence": 1,
                        "start_ratio": 0.0,
                        "end_ratio": 0.5
                    },

                    {
                        "beat_id": "scene_2_beat_2",
                        "sequence": 2,
                        "start_ratio": 0.5,
                        "end_ratio": 1.0
                    }
                ]
            }
        ]
    }

    # --------------------------------------------------------
    # Generate audio
    # --------------------------------------------------------

    files = create_audio(
        sample_json
    )

    # --------------------------------------------------------
    # Save updated JSON
    # --------------------------------------------------------

    save_timed_scene_json(
        sample_json,
        str(
            OUTPUT_DIR
            / "timed_scene.json"
        )
    )

    # --------------------------------------------------------
    # Print generated files
    # --------------------------------------------------------

    print(
        "\nGenerated files:"
    )

    for file in files:

        print(file)

    # --------------------------------------------------------
    # Print final timing
    # --------------------------------------------------------

    print(
        "\nFinal timing:"
    )

    for scene in sample_json["scenes"]:

        print(
            f"\nScene {scene['scene_id']}: "
            f"{scene['audio_duration']}s"
        )

        for beat in scene["teaching_beats"]:

            print(
                f"  Beat {beat['sequence']}: "
                f"{beat['start_time']} → "
                f"{beat['end_time']} "
                f"({beat['duration']}s)"
            )

