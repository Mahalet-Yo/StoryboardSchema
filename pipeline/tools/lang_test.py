"""Ceiling experiment E13: can the same film be narrated in Tigrinya and Afaan Oromo?

For one storyboard line (default: shot_02, the father's blessing) and each target language:
1. translate the Amharic with Gemini 3.8 Flash (the brief's "translation" stage),
2. voice it with the storyboard's TTS model and voice,
3. measure speech length against the Amharic line (does the shot still fit?),
4. check the audio is not silence.
Every call is logged to runs.jsonl. Results go to outputs/experiments/lang/results.json.
Whether it *sounds* right needs a native speaker; their verdict goes in EXPERIMENTS.md E13.

TTS quota is tiny on the free tier (FAILURES.md F2), so this makes one TTS call per language.
Usage: python -m pipeline.tools.lang_test [shot_id] [lang ...]
"""

from __future__ import annotations

import io
import json
import sys
import wave

import numpy as np
import requests

from ..common import (
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
    require_env,
    write_artifact,
)
from ..narration import _synthesise, narration_path

LANGS = {"ti": "Tigrinya", "om": "Afaan Oromo"}
# 3.8 Flash returned 503 "high demand" and timeouts on 26 Nov (FAILURES.md F10); fall back down the family.
TEXT_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]
OUT = OUTPUTS / "experiments" / "lang"


def _translate(text: str, lang_name: str, model: str):
    def call():
        prompt = (f"Translate this Amharic narration line from a short film into natural spoken {lang_name}, "
                  "as a grown daughter remembering her late father would say it aloud. Keep it warm and simple. "
                  f"Reply with the {lang_name} text only, no notes, no transliteration.\n\n{text}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            resp = requests.post(url, headers={"x-goog-api-key": require_env("GEMINI_API_KEY")},
                                 json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise TransientError(f"network: {exc}") from exc
        if not resp.ok:
            raise classify_http(resp.status_code, resp.text, resp.headers.get("Retry-After"))
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        out = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
        if not out:
            raise TransientError("empty translation")
        usage = data.get("usageMetadata", {})
        return out, {"input_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount")}, None

    return call


def _rms_db(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9))


def run(shot_id: str = "shot_02", langs: list[str] | None = None) -> list[dict]:
    board = load_storyboard()
    shot = next(s for s in board["shots"] if s["shot_id"] == shot_id)
    tts = board["providers"]["tts"]
    am_path = narration_path(shot_id)
    am_s = read_meta(am_path).get("speech_s") or media_duration(am_path)
    results = []
    for code in langs or list(LANGS):
        name = LANGS[code]
        row = {"lang": code, "language": name, "shot": shot_id, "amharic_s": round(am_s, 2)}
        try:
            tr = None
            for model in TEXT_MODELS:
                try:
                    tr = call_with_retry(_translate(shot["narration_am"], name, model), stage="experiment",
                                         artifact=f"E13:translate:{code}:{shot_id}", provider="gemini", model=model,
                                         params={"target": name}, seed=None, input_hash=None, attempts=2)
                    row["translated_by"] = model
                    break
                except PermanentError as exc:
                    print(f"  {model} unavailable for {name}: {str(exc)[:80]}")
            if tr is None:
                raise PermanentError(f"no text model could translate into {name}")
            row["text"] = tr.value
            out = OUT / f"{shot_id}.{code}.wav"
            inputs = {"text": tr.value, "voice": tts["voice"], "style": tts["style"], "lang": code}
            digest = compute_hash({"stage": "lang_test", **inputs})
            if not is_fresh(out, digest):
                res = call_with_retry(_synthesise(tts["model"], tts["voice"], tts["style"], tr.value), stage="experiment",
                                      artifact=f"E13:tts:{code}:{shot_id}", provider="gemini", model=tts["model"],
                                      params={"voice": tts["voice"], "lang": code, "chars": len(tr.value)},
                                      seed=None, input_hash=digest, attempts=2)
                write_artifact(out, res.value, digest, inputs, {"speech_s": res.units["audio_s"]})
            wav = out.read_bytes()
            speech = read_meta(out)["speech_s"]
            row.update({"file": str(out.relative_to(OUTPUTS.parent)), "speech_s": round(speech, 2),
                        "ratio_to_amharic": round(speech / am_s, 2), "rms_db": round(_rms_db(wav), 1),
                        "status": "ok"})
        except PermanentError as exc:
            row.update({"status": "failed", "error": str(exc)[:300]})
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    args = sys.argv[1:]
    run(args[0] if args else "shot_02", args[1:] or None)
