"""Shared plumbing for every stage: paths, storyboard validation, caching, retries, run log.

Every stage follows the same rules:
- read storyboard.json (validated against schema/ before anything runs),
- compute a hash of the exact inputs of each artifact,
- skip the work if the artifact and its .meta.json sidecar agree with that hash,
- otherwise call the model with retries and log every attempt to runs.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD_PATH = ROOT / "storyboard.json"
SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"
RUNS_LOG = ROOT / "runs.jsonl"
OUTPUTS = ROOT / "outputs"

RUN_ID = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:4]

# Values that must never reach the log or the console.
_SECRET_KEYS = ("GEMINI_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "HF_TOKEN")


# --------------------------------------------------------------------------- env


def load_env() -> None:
    """Load .env into os.environ without overriding variables already set."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    load_env()
    value = os.environ.get(name)
    if not value:
        raise PermanentError(f"{name} is not set. Copy .env.example to .env and fill it in.")
    return value


def redact(text: str) -> str:
    for key in _SECRET_KEYS:
        value = os.environ.get(key)
        if value and len(value) > 6:
            text = text.replace(value, f"<{key}>")
    return re.sub(r"(gh[pousr]_|hf_)[A-Za-z0-9_]{10,}", r"\1<redacted>", text)


# --------------------------------------------------------------------------- errors


class PermanentError(RuntimeError):
    """Retrying will not help (bad request, missing key, quota exhausted for the day)."""


class TransientError(RuntimeError):
    """Worth retrying (rate limit with a short wait, 5xx, timeout, empty response)."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def classify_http(status: int, body: str, retry_after: str | None = None) -> Exception:
    body = redact(body)[:400]
    wait = None
    if retry_after:
        try:
            wait = float(retry_after)
        except ValueError:
            wait = None
    if status == 429:
        # Daily quotas answer 429 with a wait of hours: retrying inside this run is pointless.
        hours = re.search(r"retry in (\d+)h", body)
        if hours or (wait is not None and wait > 120):
            return PermanentError(f"HTTP 429 quota exhausted: {body}")
        return TransientError(f"HTTP 429: {body}", wait)
    if status >= 500 or status == 408:
        return TransientError(f"HTTP {status}: {body}", wait)
    return PermanentError(f"HTTP {status}: {body}")


# --------------------------------------------------------------------------- storyboard


def load_storyboard(path: Path = STORYBOARD_PATH) -> dict:
    """Load the storyboard and validate it: JSON Schema first, then cross-references."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    board = json.loads(Path(path).read_text(encoding="utf-8"))
    jsonschema.validate(instance=board, schema=schema)
    problems = cross_check(board)
    if problems:
        raise PermanentError("storyboard.json failed cross-checks:\n  - " + "\n  - ".join(problems))
    return board


def cross_check(board: dict) -> list[str]:
    problems: list[str] = []
    ids = [s["shot_id"] for s in board["shots"]]
    if len(ids) != len(set(ids)):
        problems.append("shot_id values must be unique")
    characters = board.get("characters", {})
    for name, char in characters.items():
        base = char.get("derived_from")
        if base and base not in characters:
            problems.append(f"character {name} derives from unknown character {base}")
    for shot in board["shots"]:
        for ref in shot.get("characters", []):
            if ref not in characters:
                problems.append(f"{shot['shot_id']} uses unknown character '{ref}'")
            elif not characters[ref].get("consent", {}).get("recorded"):
                problems.append(f"{shot['shot_id']}: character '{ref}' has no consent/fictional record")
    planned = sum(s["duration_sec"] for s in board["shots"]) + board["end_card"]["duration_sec"]
    if not 60 <= planned <= 90:
        problems.append(f"planned length {planned:.1f}s is outside 60-90s")
    return problems


# --------------------------------------------------------------------------- hashing and cache


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def compute_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return sha256_bytes(serialized.encode("utf-8"))


def _meta_path(artifact: Path) -> Path:
    return artifact.with_name(artifact.name + ".meta.json")


def is_fresh(artifact: Path, input_hash: str) -> bool:
    """True when the artifact exists, was made from these exact inputs and was not altered."""
    meta = _meta_path(artifact)
    if not artifact.exists() or not meta.exists():
        return False
    try:
        info = json.loads(meta.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return info.get("input_hash") == input_hash and info.get("output_hash") == file_hash(artifact)


def write_artifact(artifact: Path, data: bytes, input_hash: str, inputs: dict, extra: dict | None = None) -> None:
    """Atomic write of the artifact and its sidecar, so a crash never leaves a half file that looks fresh."""
    artifact.parent.mkdir(parents=True, exist_ok=True)
    tmp = artifact.with_name(artifact.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, artifact)
    seal(artifact, input_hash, inputs, extra)


def seal(artifact: Path, input_hash: str, inputs: dict, extra: dict | None = None) -> None:
    """Write the sidecar for an artifact that a tool (FFmpeg) already wrote in place."""
    meta = {
        "input_hash": input_hash,
        "output_hash": file_hash(artifact),
        "run_id": RUN_ID,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inputs": inputs,
        **(extra or {}),
    }
    _meta_path(artifact).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def read_meta(artifact: Path) -> dict:
    meta = _meta_path(artifact)
    return json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}


# --------------------------------------------------------------------------- run log


def log_run(
    *,
    stage: str,
    artifact: str,
    provider: str,
    model: str,
    params: dict,
    seed: int | str | None,
    input_hash: str | None,
    attempt: int,
    status: str,
    latency_s: float,
    gpu_minutes: float | None = None,
    cost_usd: float = 0.0,
    list_price_usd: float | None = None,
    units: dict | None = None,
    error: str | None = None,
) -> None:
    """One JSON line per model call attempt (and per local render), secrets redacted."""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": RUN_ID,
        "stage": stage,
        "artifact": artifact,
        "provider": provider,
        "model": model,
        "params": params,
        "seed": seed,
        "input_hash": input_hash,
        "attempt": attempt,
        "status": status,
        "latency_s": round(latency_s, 3),
        "gpu_minutes": gpu_minutes,
        "units": units or {},
        "cost_usd": cost_usd,
        "list_price_usd": list_price_usd,
        "error": redact(error)[:500] if error else None,
    }
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@dataclass
class CallResult:
    value: Any
    latency_s: float
    attempts: int
    units: dict
    list_price_usd: float | None = None


def call_with_retry(
    fn: Callable[[], tuple[Any, dict, float | None]],
    *,
    stage: str,
    artifact: str,
    provider: str,
    model: str,
    params: dict,
    seed: int | str | None,
    input_hash: str | None,
    attempts: int = 4,
    base_delay: float = 4.0,
) -> CallResult:
    """Run fn with exponential backoff on TransientError. fn returns (value, units, list_price)."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        t0 = time.perf_counter()
        try:
            value, units, price = fn()
        except TransientError as exc:
            latency = time.perf_counter() - t0
            log_run(stage=stage, artifact=artifact, provider=provider, model=model, params=params, seed=seed,
                    input_hash=input_hash, attempt=attempt, status="retry", latency_s=latency, error=str(exc))
            last = exc
            if attempt == attempts:
                break
            delay = exc.retry_after if exc.retry_after else base_delay * 2 ** (attempt - 1)
            print(f"    transient error on {artifact} (attempt {attempt}), retrying in {delay:.0f}s: {redact(str(exc))[:120]}")
            time.sleep(min(delay, 90))
            continue
        except Exception as exc:  # permanent: log and stop at once
            latency = time.perf_counter() - t0
            log_run(stage=stage, artifact=artifact, provider=provider, model=model, params=params, seed=seed,
                    input_hash=input_hash, attempt=attempt, status="error", latency_s=latency, error=str(exc))
            raise
        latency = time.perf_counter() - t0
        log_run(stage=stage, artifact=artifact, provider=provider, model=model, params=params, seed=seed,
                input_hash=input_hash, attempt=attempt, status="ok", latency_s=latency, units=units,
                list_price_usd=price)
        return CallResult(value, latency, attempt, units, price)
    raise PermanentError(f"{artifact}: gave up after {attempts} attempts: {last}")


# --------------------------------------------------------------------------- ffmpeg


def ffmpeg_exe() -> str:
    """System FFmpeg if present, else the static build shipped with imageio-ffmpeg (has libass)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg(args: list[str], *, capture: bool = False) -> str:
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + " ".join(cmd[3:])[:300] + "\n" + proc.stderr[-1500:])
    return proc.stderr if capture else ""


def media_duration(path: Path) -> float:
    """Duration in seconds, read by decoding (no ffprobe needed)."""
    err = ffmpeg(["-i", str(path), "-f", "null", "-"], capture=True)
    times = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", err)
    if not times:
        raise RuntimeError(f"could not read duration of {path}")
    h, m, s = times[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)
