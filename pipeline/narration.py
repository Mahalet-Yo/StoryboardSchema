import base64
import json
import os
import subprocess
import time
from pathlib import Path
import jsonschema
from google import genai
from google.genai import types

from pipeline.common import SCHEMA_PATH, STORYBOARD_PATH, compute_hash, log_run

OUTPUT_DIR = Path("outputs/narration")
CACHE_DIR = Path("outputs/cache/narration")

MODEL_ID = "gemini-3.8-flash-tts"
VOICE_NAME = "Kore"


def validate_storyboard() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    storyboard = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=storyboard, schema=schema)
    return storyboard


def extract_audio_bytes(response) -> bytes:
    if getattr(response, "candidates", None):
        for cand in response.candidates:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    data = inline.data
                    return base64.b64decode(data) if isinstance(data, str) else bytes(data)
    raise ValueError("No inline audio bytes returned by Gemini TTS")


def audio_to_mp3(audio_bytes: bytes, out_mp3: Path, sample_rate: int = 24000) -> None:
    # If RIFF/WAV header is present, let FFmpeg detect container automatically; otherwise treat as 24kHz mono s16le PCM
    if audio_bytes[:4] == b"RIFF":
        cmd = ["ffmpeg", "-y", "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "s16le",
            "-ar", str(sample_rate),
            "-ac", "1",
            "-i", "pipe:0",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(out_mp3),
        ]
    proc = subprocess.run(cmd, input=audio_bytes, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio conversion failed: {proc.stderr.decode(errors='replace')}")


def run_narration() -> None:
    storyboard = validate_storyboard()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable. Set it in your local .env or environment.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version="v1beta"))
    lang = storyboard.get("language", "am")

    for shot in storyboard["shots"]:
        shot_id = shot["shot_id"]
        text = shot["narration_am"] if lang == "am" else shot["narration_en"]
        seed = shot.get("seed", 0)

        payload = {
            "stage": "narration",
            "shot_id": shot_id,
            "model": MODEL_ID,
            "voice": VOICE_NAME,
            "language": lang,
            "text": text,
            "seed": seed,
        }
        digest = compute_hash(payload)
        marker = CACHE_DIR / f"{shot_id}_{digest}.json"
        out_mp3 = OUTPUT_DIR / f"{shot_id}.mp3"

        if marker.exists() and out_mp3.exists():
            print(f"Cached: {shot_id} ({out_mp3})")
            continue

        t0 = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
                        )
                    ),
                ),
            )
            latency = time.perf_counter() - t0
            audio_bytes = extract_audio_bytes(response)
            audio_to_mp3(audio_bytes, out_mp3)
            marker.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            log_run(
                stage="narration",
                model=MODEL_ID,
                parameters={"shot_id": shot_id, "voice": VOICE_NAME, "language": lang, "chars": len(text)},
                seed=seed,
                latency_sec=latency,
                cost_usd=0.0,
                status="ok",
            )
            print(f"Generated {out_mp3} in {latency:.2f}s")
        except Exception as exc:
            latency = time.perf_counter() - t0
            log_run(
                stage="narration",
                model=MODEL_ID,
                parameters={"shot_id": shot_id, "voice": VOICE_NAME, "language": lang, "chars": len(text)},
                seed=seed,
                latency_sec=latency,
                cost_usd=0.0,
                status=f"error: {exc}",
            )
            print(f"Failed {shot_id}: {exc}")


if __name__ == "__main__":
    run_narration()
