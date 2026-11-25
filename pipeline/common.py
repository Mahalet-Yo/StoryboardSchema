import hashlib
import json
import time
from pathlib import Path
import jsonschema

STORYBOARD_PATH = Path("storyboard.json")
SCHEMA_PATH = Path("schema/storyboard.schema.json")
RUNS_LOG = Path("runs.jsonl")


def load_and_validate_storyboard() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    storyboard = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=storyboard, schema=schema)
    return storyboard


def compute_hash(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def log_run(
    stage: str,
    model: str,
    parameters: dict,
    seed: int | str | None,
    latency_sec: float,
    cost_usd: float = 0.0,
    status: str = "ok",
) -> None:
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stage": stage,
        "model": model,
        "parameters": parameters,
        "seed": seed,
        "latency_sec": round(latency_sec, 3),
        "cost_usd": cost_usd,
        "status": status,
    }
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
