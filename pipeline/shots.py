"""Stage: moving shots. One silent H.264 segment per shot and aspect ratio, exactly as long as the timeline says.

Motion is a slow eased pan/zoom over the keyframe (Ken Burns), rendered by FFmpeg. The camera move
comes from `camera_move` in the storyboard. Consecutive shots alternate direction in the storyboard
so the film does not feel like one long zoom. The segment's cache key includes the keyframe's
content hash, so a new keyframe re-renders only its own segment.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .common import OUTPUTS, compute_hash, ffmpeg, file_hash, is_fresh, load_storyboard, log_run, rel, seal
from .keyframes import aspect_tag, keyframe_path

CLIP_DIR = OUTPUTS / "clips"
OUT_SIZE = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
OVERSAMPLE = 1.5  # zoompan rounds to whole pixels; working larger than the output removes the jitter
ZOOM = 0.10


def clip_path(shot_id: str, aspect: str) -> Path:
    return CLIP_DIR / f"{shot_id}.{aspect_tag(aspect)}.mp4"


def _move(move: str, frames: int) -> tuple[str, str, str]:
    p = f"(on/{max(frames - 1, 1)})"
    e = f"({p}*{p}*(3-2*{p}))"  # smoothstep: starts and ends gently
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    z = f"{1 + ZOOM:.3f}"
    if move == "push_in":
        return f"1+{ZOOM}*{e}", cx, cy
    if move == "pull_out":
        return f"{1 + ZOOM}-{ZOOM}*{e}", cx, cy
    if move == "pan_right":
        return z, f"(iw-iw/zoom)*{e}", cy
    if move == "pan_left":
        return z, f"(iw-iw/zoom)*(1-{e})", cy
    if move == "tilt_up":
        return z, cx, f"(ih-ih/zoom)*(1-{e})"
    if move == "tilt_down":
        return z, cx, f"(ih-ih/zoom)*{e}"
    return f"1.02+0.02*{e}", cx, cy  # hold: barely breathing


def render(src: Path, out: Path, move: str, duration: float, aspect: str, fps: int) -> None:
    w, h = OUT_SIZE[aspect]
    W, H = int(w * OVERSAMPLE) // 2 * 2, int(h * OVERSAMPLE) // 2 * 2
    frames = round(duration * fps)
    z, x, y = _move(move, frames)
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps},"
          f"format=yuv420p,setsar=1")
    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(["-loop", "1", "-i", str(src), "-vf", vf, "-frames:v", str(frames), "-r", str(fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-an", str(out)])


def run(board: dict | None = None, timeline: dict | None = None) -> int:
    board = board or load_storyboard()
    if timeline is None:
        timeline = json.loads((OUTPUTS / "timeline.json").read_text(encoding="utf-8"))
    fps = timeline["fps"]
    lengths = {s["shot_id"]: s["duration"] for s in timeline["shots"]}
    made = 0
    for shot in board["shots"]:
        sid = shot["shot_id"]
        for aspect in board["aspect_ratios"]:
            src = keyframe_path(sid, aspect)
            out = clip_path(sid, aspect)
            inputs = {"keyframe": file_hash(src), "move": shot["camera_move"], "duration": lengths[sid],
                      "aspect": aspect, "fps": fps, "zoom": ZOOM, "oversample": OVERSAMPLE, "provider": "kenburns"}
            digest = compute_hash({"stage": "shots", **inputs})
            if is_fresh(out, digest):
                continue
            t0 = time.perf_counter()
            render(src, out, shot["camera_move"], lengths[sid], aspect, fps)
            latency = time.perf_counter() - t0
            seal(out, digest, inputs, {"provider": "kenburns"})
            log_run(stage="shots", artifact=f"{sid}.{aspect_tag(aspect)}", provider="local", model="ffmpeg-zoompan",
                    params={"move": shot["camera_move"], "duration": lengths[sid], "aspect": aspect},
                    seed=None, input_hash=digest, attempt=1, status="ok", latency_s=latency)
            made += 1
            print(f"  clip {sid}.{aspect_tag(aspect)}: {shot['camera_move']} {lengths[sid]:.2f}s rendered in {latency:.1f}s")
    total = len(board["shots"]) * len(board["aspect_ratios"])
    print(f"shots: {made} rendered, {total - made} cached -> {rel(CLIP_DIR)}")
    return made


if __name__ == "__main__":
    run()
