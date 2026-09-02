import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

OUTPUT_DIR = BASE_DIR / "generated_video"

OUTPUT_DIR.mkdir(
    exist_ok=True
)


def concatenate_audio(
    audio_files: list[str],
    output_audio: str
):
    if not audio_files:
        raise ValueError(
            "No audio files provided."
        )

    file_list = OUTPUT_DIR / "audio_files.txt"

    with open(
        file_list,
        "w",
        encoding="utf-8"
    ) as f:

        for audio in audio_files:

            audio_path = Path(
                audio
            ).resolve()

            f.write(
                f"file '{audio_path}'\n"
            )

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(file_list),
        "-c:a",
        "libmp3lame",
        output_audio
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    file_list.unlink(
        missing_ok=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Audio concatenation failed:\n"
            + result.stderr
        )

    print(
        f"Combined audio created: {output_audio}"
    )

    return output_audio


def merge_video_audio(
    video_path: str,
    audio_path: str,
    output_path: str
):

    command = [
        "ffmpeg",
        "-y",

        "-i",
        str(video_path),

        "-i",
        str(audio_path),

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "copy",

        "-c:a",
        "aac",

        "-shortest",

        output_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Video/audio merge failed:\n"
            + result.stderr
        )

    print(
        f"Final video created: {output_path}"
    )

    return output_path


def create_final_video(
    video_path: str,
    audio_files: list[str]
):

    combined_audio = str(
        OUTPUT_DIR / "combined_narration.mp3"
    )

    final_video = str(
        OUTPUT_DIR / "final_learning_video.mp4"
    )

    concatenate_audio(
        audio_files=audio_files,
        output_audio=combined_audio
    )

    merge_video_audio(
        video_path=video_path,
        audio_path=combined_audio,
        output_path=final_video
    )

    return final_video