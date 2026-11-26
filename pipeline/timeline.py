"""Timeline: measured narration sets shot lengths (professionals cut picture to the voice track).

Each shot lasts max(planned duration, LEAD + speech + TAIL), rounded up to whole frames.
The film (shots + end card) must land inside 60-90 s or the run stops.
"""

from __future__ import annotations

import json
import math

from .common import OUTPUTS, PermanentError

LEAD_S = 0.7   # silence before the line starts, so a cut never clips the first syllable
TAIL_S = 1.1   # breath after the line before the next cut


def build(board: dict, speech: dict[str, float], fps: int = 24) -> dict:
    t = 0.0
    shots = []
    for shot in board["shots"]:
        sid = shot["shot_id"]
        need = LEAD_S + speech[sid] + TAIL_S
        dur = max(float(shot["duration_sec"]), need)
        dur = math.ceil(dur * fps) / fps
        shots.append({"shot_id": sid, "start": round(t, 4), "duration": round(dur, 4),
                      "speech_start": round(t + LEAD_S, 4), "speech_s": round(speech[sid], 3),
                      "stretched": dur > shot["duration_sec"] + 1e-6,
                      "music_cue": shot["music_cue"]})
        t += dur
    end = float(board["end_card"]["duration_sec"])
    total = t + end
    if not 60 <= total <= 90:
        raise PermanentError(f"timeline is {total:.1f}s; the film must be 60-90 s. Shorten or lengthen shots.")
    cues = []
    for cue in board["music"]["cues"]:
        start = next(s["start"] for s in shots if s["shot_id"] == cue["from_shot"])
        cues.append({**cue, "start": start})
    timeline = {"fps": fps, "shots": shots, "end_card": {"start": round(t, 4), "duration": end},
                "total": round(total, 4), "cues": cues}
    out = OUTPUTS / "timeline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    return timeline
