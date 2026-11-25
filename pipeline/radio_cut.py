import json
import os
import subprocess
import time
from pathlib import Path

STORYBOARD_PATH = Path("storyboard.json")
NARRATION_DIR = Path("outputs/narration")
OUTPUT_DIR = Path("outputs")
TEMP_DIR = Path("outputs/temp_radio")
PLACEHOLDER_MUSIC = Path("assets/temp_music.mp3")
FINAL_OUTPUT = OUTPUT_DIR / "radio_cut.mp4"
RUNS_LOG = Path("runs.jsonl")


def log_run(stage: str, duration_sec: float, output_file: str):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stage": stage,
        "model": "ffmpeg-local",
        "latency_sec": round(duration_sec, 2),
        "cost_usd": 0.0,
        "output": output_file,
    }
    with open(RUNS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def run_cmd(cmd: list[str]):
    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )


def build_radio_cut():
    start_time = time.time()
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(STORYBOARD_PATH, "r", encoding="utf-8") as f:
        storyboard = json.load(f)

    shots = storyboard.get("shots", [])
    if not shots:
        raise ValueError("No shots found in storyboard.json")

    concat_list_path = TEMP_DIR / "concat.txt"
    total_duration = 0.0

    # 1. Pad or trim each shot's narration to match the storyboard shot duration
    with open(concat_list_path, "w", encoding="utf-8") as concat_file:
        for idx, shot in enumerate(shots):
            shot_id = shot.get("id", f"shot_{idx+1:02d}")
            duration = float(shot.get("duration", 5.0))
            total_duration += duration

            narration_file = NARRATION_DIR / f"{shot_id}.mp3"
            padded_clip = TEMP_DIR / f"{shot_id}_padded.wav"

            if narration_file.exists():
                # Pad narration with silence to fit exact shot duration
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(narration_file),
                    "-af",
                    f"apad=whole_dur={duration}",
                    "-t",
                    str(duration),
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    str(padded_clip),
                ]
            else:
                # Generate pure silence if shot has no narration
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=r=44100:cl=stereo",
                    "-t",
                    str(duration),
                    str(padded_clip),
                ]
            run_cmd(cmd)
            concat_file.write(f"file '{padded_clip.resolve().as_posix()}'\n")

    # 2. Concatenate all shot voice tracks into one continuous narration track
    full_voice_track = TEMP_DIR / "full_narration.wav"
    run_cmd([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list_path),
        "-c",
        "copy",
        str(full_voice_track),
    ])

    # 3. Prepare placeholder background music (use file if present, else generate soft tone)
    bg_music_track = TEMP_DIR / "bg_music.wav"
    if PLACEHOLDER_MUSIC.exists():
        run_cmd([
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(PLACEHOLDER_MUSIC),
            "-t",
            str(total_duration),
            "-af",
            "volume=0.15",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(bg_music_track),
        ])
    else:
        run_cmd([
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=220:duration={total_duration}",
            "-af",
            "volume=0.03",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(bg_music_track),
        ])

    # 4. Mix narration + ducked music over a 1280x720 black screen
    run_cmd([
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s=1280x720:r=24:d={total_duration}",
        "-i",
        str(full_voice_track),
        "-i",
        str(bg_music_track),
        "-filter_complex",
        "[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(FINAL_OUTPUT),
    ])

    elapsed = time.time() - start_time
    log_run("radio_cut", elapsed, str(FINAL_OUTPUT))
    print(
        f"Radio cut created at {FINAL_OUTPUT} ({total_duration:.1f}s) in"
        f" {elapsed:.2f}s"
    )


if __name__ == "__main__":
    build_radio_cut()
