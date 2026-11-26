"""Stage: narration. One WAV per shot from Gemini TTS, cached by text + voice + style + model + take.

Gemini TTS moved to the Interactions API (/v1beta/interactions); the old generateContent +
speechConfig request now fails with 400 (FAILURES.md F1). There is no seed, so `narration_take`
in the storyboard stands in for one: bump it to ask for a new performance of the same line.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import requests

from .common import (
    OUTPUTS,
    PermanentError,
    TransientError,
    call_with_retry,
    classify_http,
    compute_hash,
    is_fresh,
    load_storyboard,
    media_duration,
    read_meta,
    rel,
    require_env,
    write_artifact,
)

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
OUT_DIR = OUTPUTS / "narration"
SAMPLE_RATE = 24_000
# List price per token (USD), for COSTS.md; real spend on the free tier is zero.
LIST_PRICE = {"gemini-3.8-flash-tts": (0.50e-6, 9.00e-6), "gemini-3.8-flash-lite-tts": (0.50e-6, 6.00e-6)}
AUDIO_TOKENS_PER_SECOND = 25


def narration_path(shot_id: str) -> Path:
    return OUT_DIR / f"{shot_id}.wav"


def _synthesise(model: str, voice: str, style: str, text: str):
    def call():
        body = {
            "store": False,
            "model": model,
            "input": [{"type": "user_input", "content": [
                {"type": "text", "text": text, "annotations": [{"type": "speech_metadata", "style": style}]}
            ]}],
            "response_format": {"type": "audio", "mime_type": "audio/wav", "sample_rate": SAMPLE_RATE},
            "generation_config": {"speech_config": [{"voice": voice}]},
        }
        try:
            resp = requests.post(URL, json=body, headers={"x-goog-api-key": require_env("GEMINI_API_KEY")}, timeout=180)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise TransientError(f"network: {exc}") from exc
        if not resp.ok:
            raise classify_http(resp.status_code, resp.text, resp.headers.get("Retry-After"))
        data = resp.json()
        audio = [c for s in data.get("steps", []) if s.get("type") == "model_output"
                 for c in s.get("content", []) if c.get("type") == "audio"]
        if not audio:
            raise TransientError(f"no audio in response (status={data.get('status')})")
        wav = base64.b64decode(audio[-1]["data"])
        if wav[:4] != b"RIFF":
            raise PermanentError("expected a WAV container from TTS")
        seconds = (len(wav) - 44) / (SAMPLE_RATE * 2)
        usage = data.get("usage") or {}
        units = {"input_tokens": usage.get("total_input_tokens"), "output_tokens": usage.get("total_output_tokens"),
                 "audio_s": round(seconds, 3)}
        price = None
        if model in LIST_PRICE:
            p_in, p_out = LIST_PRICE[model]
            out_tokens = units["output_tokens"] or seconds * AUDIO_TOKENS_PER_SECOND
            price = round((units["input_tokens"] or len(text)) * p_in + out_tokens * p_out, 6)
        return wav, units, price

    return call


def run(board: dict | None = None) -> dict[str, float]:
    """Generate missing or changed lines. Returns {shot_id: speech seconds}."""
    board = board or load_storyboard()
    tts = board["providers"]["tts"]
    models = [tts["model"], *tts.get("fallback_models", [])]
    durations: dict[str, float] = {}
    made = 0
    for shot in board["shots"]:
        sid = shot["shot_id"]
        text = shot["narration_am"] if board["language"] == "am" else shot["narration_en"]
        inputs = {"text": text, "voice": tts["voice"], "style": tts["style"], "take": shot.get("narration_take", 1)}
        out = narration_path(sid)
        # The model is deliberately not part of the hash: a line made by the fallback model stays valid.
        digest = compute_hash({"stage": "narration", **inputs})
        if is_fresh(out, digest):
            durations[sid] = read_meta(out).get("speech_s") or media_duration(out)
            print(f"  narration {sid}: cached")
            continue
        last_error: Exception | None = None
        for model in models:
            try:
                result = call_with_retry(
                    _synthesise(model, tts["voice"], tts["style"], text),
                    stage="narration", artifact=sid, provider="gemini", model=model,
                    params={"voice": tts["voice"], "style": tts["style"], "take": inputs["take"], "chars": len(text)},
                    seed=None, input_hash=digest,
                )
            except PermanentError as exc:
                last_error = exc
                print(f"  narration {sid}: {model} unavailable ({str(exc)[:90]}), trying next model")
                continue
            write_artifact(out, result.value, digest, inputs, {"model": model, "speech_s": result.units["audio_s"]})
            durations[sid] = result.units["audio_s"]
            made += 1
            print(f"  narration {sid}: {model} {result.units['audio_s']:.1f}s of speech in {result.latency_s:.1f}s")
            break
        else:
            raise PermanentError(f"narration {sid}: every TTS model failed: {last_error}")
        time.sleep(0.5)
    print(f"narration: {made} generated, {len(durations) - made} cached -> {rel(OUT_DIR)}")
    return durations


if __name__ == "__main__":
    run()
