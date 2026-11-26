"""Experiment E8: how much does each ducking setting lower the music under the real narration?

For each setting, the selected score is ducked by the narration stem exactly as assemble does it.
The ducked music alone is then measured in two kinds of window from timeline.json:
- under speech (the voice is talking): we want the music clearly lower here,
- in pauses (between lines): we want the music back up, not pumping or vanishing.
Writes outputs/experiments/duck_sweep.json and prints a table for EXPERIMENTS.md.
"""

from __future__ import annotations

import json
import os
import wave

import numpy as np

from ..common import OUTPUTS, ROOT, ffmpeg

SETTINGS = [
    {"name": "none", "threshold": 1.0, "ratio": 1, "attack_ms": 20, "release_ms": 250},
    {"name": "brief default", "threshold": 0.02, "ratio": 6, "attack_ms": 300, "release_ms": 1500},
    {"name": "gentle", "threshold": 0.05, "ratio": 4, "attack_ms": 120, "release_ms": 900},
    {"name": "soft", "threshold": 0.1, "ratio": 3, "attack_ms": 100, "release_ms": 700},
]


def _read(path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
        return x.reshape(-1, w.getnchannels()).mean(1), w.getframerate()


def _db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9))


def run() -> list[dict]:
    os.chdir(ROOT)
    tl = json.loads((OUTPUTS / "timeline.json").read_text(encoding="utf-8"))
    voice, music = OUTPUTS / "audio" / "narration_stem.wav", OUTPUTS / "audio" / "music_stem.wav"
    if not (voice.exists() and music.exists()):
        raise SystemExit("run `make film` first: the sweep uses the real narration and music stems")
    out_dir = OUTPUTS / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)
    speech = [(s["speech_start"], s["speech_start"] + s["speech_s"]) for s in tl["shots"]]
    pauses = [(a[1] + 0.3, b[0] - 0.3) for a, b in zip(speech, speech[1:]) if b[0] - a[1] > 1.0]
    rows = []
    for st in SETTINGS:
        tmp = out_dir / "ducked.tmp.wav"
        ffmpeg(["-i", str(voice), "-i", str(music), "-filter_complex",
                f"[1:a][0:a]sidechaincompress=threshold={st['threshold']}:ratio={st['ratio']}:"
                f"attack={st['attack_ms']}:release={st['release_ms']}[d]", "-map", "[d]", str(tmp)])
        x, sr = _read(tmp)
        under = np.concatenate([x[int(a * sr):int(b * sr)] for a, b in speech])
        gaps = np.concatenate([x[int(a * sr):int(b * sr)] for a, b in pauses])
        rows.append({**st, "music_under_speech_db": round(_db(under), 1), "music_in_pauses_db": round(_db(gaps), 1)})
        tmp.unlink()
    base = rows[0]
    for r in rows:
        r["duck_depth_db"] = round(base["music_under_speech_db"] - r["music_under_speech_db"], 1)
        r["pause_loss_db"] = round(base["music_in_pauses_db"] - r["music_in_pauses_db"], 1)
    (out_dir / "duck_sweep.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("| Setting | threshold / ratio / attack / release | Music under speech | Duck depth | Music lost in pauses |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['name']} | {r['threshold']} / {r['ratio']} / {r['attack_ms']} ms / {r['release_ms']} ms | "
              f"{r['music_under_speech_db']} dBFS | {r['duck_depth_db']} dB | {r['pause_loss_db']} dB |")
    return rows


if __name__ == "__main__":
    run()
