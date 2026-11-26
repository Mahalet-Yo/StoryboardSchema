"""Stage: music. Score candidates, one per seed; the storyboard names the chosen seed.

Provider order:
1. ACE-Step 1.5 on its public Hugging Face Space (no GPU of our own: no Kaggle token on this
   machine). Tried first on every uncached run; every attempt is logged.
2. `synth`: a small seeded composer in NumPy. Krar-like plucked strings (Karplus-Strong) in the
   tezeta pentatonic mode over a low drone and a soft pad, following the storyboard's spotting
   cues so the texture opens at the time jump and resolves under the end card. Deterministic:
   the same seed and timeline give the same file. Used when ACE-Step is unavailable
   (FAILURES.md F4).

Each candidate is scored for how much room it leaves the voice (energy share in the
300-3400 Hz speech band, lower is better) and written to outputs/music/candidates.json.
"""

from __future__ import annotations

import io
import json
import time
import wave
from pathlib import Path

import numpy as np

from .common import (
    OUTPUTS,
    PermanentError,
    call_with_retry,
    compute_hash,
    is_fresh,
    load_storyboard,
    log_run,
    rel,
    write_artifact,
)

OUT_DIR = OUTPUTS / "music"
SR = 44_100
# Tezeta (major) pentatonic on C: C D E G A. MIDI numbers over three octaves.
TEZETA = [0, 2, 4, 7, 9]


def candidate_path(seed: int) -> Path:
    return OUT_DIR / f"score.seed{seed}.wav"


def selected_path(board: dict) -> Path:
    return candidate_path(board["music"]["selected_seed"])


# --------------------------------------------------------------------------- synth composer


def _midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _pluck(freq: float, dur: float, rng: np.random.Generator, bright: float) -> np.ndarray:
    """Karplus-Strong plucked string, close to a krar's bright, quickly decaying note."""
    n = int(SR * dur)
    period = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, period) * bright
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.996 * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out * np.exp(-np.linspace(0, 3.2, n))


def _pad(freqs: list[float], dur: float, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    sig = np.zeros_like(t)
    for f in freqs:
        for detune in (-0.12, 0.0, 0.13):
            phase = rng.uniform(0, 2 * np.pi)
            sig += np.sin(2 * np.pi * (f + detune) * t + phase) * 0.33
            sig += 0.12 * np.sin(2 * np.pi * 2 * (f + detune) * t + phase)
    env = np.minimum(1, t / 2.5) * np.minimum(1, (dur - t) / 2.5).clip(0)
    return sig * env / max(1, len(freqs))


def compose(seed: int, timeline: dict, bpm: int) -> bytes:
    rng = np.random.default_rng(seed)
    total = timeline["total"] + 1.0
    n = int(SR * total)
    mix = np.zeros((n, 2))
    beat = 60.0 / bpm
    cue_starts = {c["id"]: c["start"] for c in timeline["cues"]}
    order = sorted(cue_starts.items(), key=lambda kv: kv[1])

    def section(t: float) -> str:
        current = order[0][0]
        for cid, start in order:
            if t >= start:
                current = cid
        return current

    # Intensity per section: (pluck density, pad level, drone level, register shift)
    shape = {
        "memory": (0.45, 0.25, 0.55, 0),
        "time_passes": (0.35, 0.65, 0.6, -12),
        "fulfilment": (0.7, 0.8, 0.6, 0),
        "resolution": (0.3, 0.4, 0.5, 0),
    }
    root = 48  # C3: the key is fixed by the storyboard (C tezeta); the seed varies the line, not the key

    # Drone: tonic and fifth, slow breathing.
    t = np.arange(n) / SR
    breath = 0.75 + 0.25 * np.sin(2 * np.pi * t / (beat * 16) + rng.uniform(0, 6))
    drone = (np.sin(2 * np.pi * _midi_hz(root - 12) * t) + 0.5 * np.sin(2 * np.pi * _midi_hz(root - 5) * t)) * breath
    fade = np.minimum(1, t / 3.0) * np.clip((total - t) / 4.0, 0, 1)
    drone_level = np.array([shape.get(section(x), shape["memory"])[2] for x in t[:: SR // 10]])
    drone_level = np.repeat(drone_level, SR // 10)[:n]
    drone *= drone_level * fade * 0.18
    mix += drone[:, None]

    # Pad chords every 4 bars, drawn from the mode.
    chords = [[0, 4, 7], [9, 12, 16], [7, 11, 14], [2, 7, 9]]
    bar = beat * 4
    pos = 0.0
    i = int(rng.integers(0, len(chords)))
    while pos < total:
        lvl = shape.get(section(pos), shape["memory"])[1]
        dur = min(bar * 4, total - pos)
        if dur < 1:
            break
        ch = [_midi_hz(root + 12 + iv + (shape.get(section(pos), shape["memory"])[3])) for iv in chords[i % len(chords)]]
        seg = _pad(ch, dur + 2.0, rng) * lvl * 0.16
        a = int(pos * SR)
        b = min(n, a + len(seg))
        pan = 0.15 * np.sin(i)
        mix[a:b, 0] += seg[: b - a] * (1 - pan)
        mix[a:b, 1] += seg[: b - a] * (1 + pan)
        pos += bar * 4
        i += int(rng.integers(1, 3))

    # Krar line: a slow motif in the mode, repeated with variation (the leitmotif returns at the end).
    scale = [root + 24 + o * 12 + d for o in (0, 1) for d in TEZETA]
    motif = list(rng.choice(len(scale) - 3, size=6))
    step = beat / 2
    pos = 1.0
    k = 0
    while pos < total - 2:
        sec = section(pos)
        density = shape.get(sec, shape["memory"])[0]
        if rng.random() < density:
            idx = motif[k % len(motif)] + (int(rng.integers(-1, 2)) if k >= len(motif) else 0)
            idx = int(np.clip(idx, 0, len(scale) - 1))
            if sec == "resolution" and pos > total - 6:
                idx = 0  # land on the tonic under the end card
            note = _pluck(_midi_hz(scale[idx]), min(2.4, total - pos), rng, 0.55 + 0.3 * density)
            a = int(pos * SR)
            b = min(n, a + len(note))
            pan = rng.uniform(-0.35, 0.35)
            mix[a:b, 0] += note[: b - a] * 0.22 * (1 - pan)
            mix[a:b, 1] += note[: b - a] * 0.22 * (1 + pan)
        pos += step * (2 if rng.random() < 0.35 else 1)
        k += 1

    # Light room reverb: a few decaying echoes.
    wet = np.zeros_like(mix)
    for delay, gain in ((0.043, 0.35), (0.071, 0.28), (0.113, 0.22), (0.187, 0.15), (0.29, 0.1)):
        d = int(delay * SR)
        wet[d:] += mix[:-d] * gain
    mix = mix + wet * 0.6
    mix /= max(1e-9, np.abs(mix).max()) / 0.8
    pcm = (mix * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def voice_band_share(wav_bytes: bytes) -> float:
    """Energy share inside 300-3400 Hz. Lower leaves more room for narration."""
    with wave.open(io.BytesIO(wav_bytes)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float).reshape(-1, w.getnchannels()).mean(1)
        sr = w.getframerate()
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / sr)
    band = spec[(freqs >= 300) & (freqs <= 3400)].sum()
    return float(band / max(spec.sum(), 1e-9))


# --------------------------------------------------------------------------- ACE-Step


def _ace_step(board: dict, seed: int, duration: float):
    def call():
        from gradio_client import Client

        prov = board["providers"]["music"]
        client = Client(prov.get("space", "ACE-Step/Ace-Step-v1.5"), verbose=False)
        api = client.view_api(return_format="dict", print_info=False)["named_endpoints"]["/generation_wrapper"]
        args = [p.get("parameter_default") for p in api["parameters"]]
        m = board["music"]
        for k, v in {4: m["caption"], 5: "[Instrumental]", 6: m["bpm"], 10: prov.get("infer_steps", 8),
                     12: False, 13: str(seed), 15: round(duration), 16: 1}.items():
            args[k] = v
        result = client.predict(*args, api_name="/generation_wrapper")
        audio = result[0]
        if not audio:
            raise PermanentError(f"ACE-Step Space returned no audio: {str(result[8:11])[:300]}")
        path = audio if isinstance(audio, str) else audio.get("path")
        return Path(path).read_bytes(), {"duration_s": duration}, None

    return call


# --------------------------------------------------------------------------- stage


def run(board: dict | None = None, timeline: dict | None = None) -> Path:
    board = board or load_storyboard()
    if timeline is None:
        timeline = json.loads((OUTPUTS / "timeline.json").read_text(encoding="utf-8"))
    m = board["music"]
    provider = board["providers"]["music"]["provider"]
    ace_down = False
    report = []
    for seed in m["candidate_seeds"]:
        out = candidate_path(seed)
        inputs = {"caption": m["caption"], "bpm": m["bpm"], "key": m.get("key"), "seed": seed,
                  "length": round(timeline["total"], 2), "cues": [[c["id"], c["start"]] for c in timeline["cues"]],
                  "provider": provider}
        digest = compute_hash({"stage": "music", **inputs})
        if not is_fresh(out, digest):
            data, used = None, None
            if provider == "ace-step-space" and not ace_down:
                try:
                    res = call_with_retry(_ace_step(board, seed, timeline["total"] + 1), stage="music",
                                          artifact=f"score.seed{seed}", provider="hf-space",
                                          model="ACE-Step 1.5 (xl-turbo)", params={"caption": m["caption"], "bpm": m["bpm"]},
                                          seed=seed, input_hash=digest, attempts=2)
                    data, used = res.value, "ace-step-1.5"
                except Exception as exc:  # noqa: BLE001 - any Space failure means fall back
                    ace_down = True
                    print(f"  music: ACE-Step Space unavailable ({str(exc)[:100]}); using the synth composer")
            if data is None:
                t0 = time.perf_counter()
                data, used = compose(seed, timeline, m["bpm"]), "synth-tezeta-v1"
                log_run(stage="music", artifact=f"score.seed{seed}", provider="local", model=used,
                        params={"bpm": m["bpm"], "key": m.get("key"), "length_s": round(timeline["total"], 2)},
                        seed=seed, input_hash=digest, attempt=1, status="ok", latency_s=time.perf_counter() - t0)
            write_artifact(out, data, digest, inputs, {"model": used})
            print(f"  music seed {seed}: {used}")
        else:
            print(f"  music seed {seed}: cached")
        share = voice_band_share(out.read_bytes()) if out.suffix == ".wav" else None
        report.append({"seed": seed, "file": rel(out), "voice_band_share": round(share, 4) if share else None,
                       "selected": seed == m["selected_seed"]})
    (OUT_DIR / "candidates.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    chosen = selected_path(board)
    if not chosen.exists():
        raise PermanentError(f"selected_seed {m['selected_seed']} is not among candidate_seeds")
    print(f"music: {len(report)} candidates, selected seed {m['selected_seed']} -> {rel(chosen)}")
    return chosen


if __name__ == "__main__":
    run()
