"""Stage: reference sheet, then keyframes. FLUX.2 klein on Cloudflare Workers AI.

Order matters for consistency:
1. one reference portrait per character (a derived character, the grown daughter, is
   conditioned on the child's reference so the two read as one person);
2. every 9:16 keyframe is conditioned on the references of the characters in the shot;
3. the 16:9 keyframe is conditioned on the 9:16 keyframe plus the same references, so the two
   aspect ratios show the same moment instead of two different pictures.

Reference images enter the cache hash by content: regenerating a reference invalidates every
keyframe that uses it, and a new 9:16 keyframe invalidates its 16:9 sibling. Nothing else reruns.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import requests
from PIL import Image

from .common import (
    OUTPUTS,
    PermanentError,
    TransientError,
    call_with_retry,
    classify_http,
    compute_hash,
    file_hash,
    is_fresh,
    load_storyboard,
    rel,
    require_env,
    write_artifact,
)

REF_DIR = OUTPUTS / "references"
KEY_DIR = OUTPUTS / "keyframes"
SIZES = {"9:16": (768, 1344), "16:9": (1344, 768), "ref": (768, 768)}
NEURONS_PER_OUT_TILE = 26.05  # 512x512 output tile, FLUX.2 klein 4B list price
NEURONS_PER_IN_TILE = 5.37
USD_PER_1K_NEURONS = 0.011
FLAGGED_SEED_TRIES = 3


def aspect_tag(aspect: str) -> str:
    return "v" if aspect == "9:16" else "h"


def keyframe_path(shot_id: str, aspect: str) -> Path:
    return KEY_DIR / f"{shot_id}.{aspect_tag(aspect)}.png"


def reference_path(name: str) -> Path:
    return REF_DIR / f"{name}.png"


def _shrink(path: Path, max_px: int) -> bytes:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _tiles(w: int, h: int) -> int:
    return -(-w // 512) * -(-h // 512)


def _generate(model: str, prompt: str, size: tuple[int, int], seed: int, steps: int, refs: list[bytes]):
    def call():
        fields = {"prompt": (None, prompt), "width": (None, str(size[0])), "height": (None, str(size[1])),
                  "seed": (None, str(seed)), "steps": (None, str(steps))}
        for i, ref in enumerate(refs[:4]):
            fields[f"input_image_{i}"] = (f"ref{i}.png", ref, "image/png")
        url = f"https://api.cloudflare.com/client/v4/accounts/{require_env('CLOUDFLARE_ACCOUNT_ID')}/ai/run/{model}"
        try:
            resp = requests.post(url, headers={"Authorization": f"Bearer {require_env('CLOUDFLARE_API_TOKEN')}"},
                                 files=fields, timeout=180)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise TransientError(f"network: {exc}") from exc
        if not resp.ok:
            raise classify_http(resp.status_code, resp.text, resp.headers.get("Retry-After"))
        image = (resp.json().get("result") or {}).get("image")
        if not image:
            raise TransientError("no image in response")
        data = base64.b64decode(image)
        got = Image.open(io.BytesIO(data)).size
        if got != size:
            raise PermanentError(f"asked for {size}, got {got}")
        neurons = _tiles(*size) * NEURONS_PER_OUT_TILE + len(refs) * 1 * NEURONS_PER_IN_TILE
        return data, {"neurons_est": round(neurons, 1), "refs": len(refs)}, round(neurons / 1000 * USD_PER_1K_NEURONS, 5)

    return call


def _make(stage_artifact: str, out: Path, prompt: str, size, seed: int, refs: list[Path], board: dict) -> bool:
    img = board["providers"]["image"]
    max_px = img.get("reference_max_px", 496)
    inputs = {"prompt": prompt, "size": list(size), "seed": seed, "steps": img["steps"], "model": img["model"],
              "refs": [file_hash(r) for r in refs], "ref_max_px": max_px}
    digest = compute_hash({"stage": "keyframes", **inputs})
    if is_fresh(out, digest):
        return False
    ref_bytes = [_shrink(r, max_px) for r in refs]
    # The provider's output safety filter sometimes flags harmless family scenes (FAILURES.md F3).
    # It judges the output, so a different seed of the same prompt usually passes. The derived
    # seeds are deterministic, so a clean re-run reproduces the same image.
    for n, try_seed in enumerate(seed + k * 1000 for k in range(FLAGGED_SEED_TRIES)):
        try:
            result = call_with_retry(
                _generate(img["model"], prompt, size, try_seed, img["steps"], ref_bytes),
                stage="keyframes", artifact=stage_artifact, provider="cloudflare", model=img["model"],
                params={"size": f"{size[0]}x{size[1]}", "steps": img["steps"], "refs": [rel(r) for r in refs],
                        "prompt": prompt[:200]},
                seed=try_seed, input_hash=digest,
            )
        except PermanentError as exc:
            if "flagged" in str(exc) and n + 1 < FLAGGED_SEED_TRIES:
                print(f"  {stage_artifact}: output flagged by the provider filter at seed {try_seed}, trying next seed")
                continue
            raise
        write_artifact(out, result.value, digest, inputs, {"seed_used": try_seed})
        print(f"  {stage_artifact}: generated in {result.latency_s:.1f}s (seed {try_seed})")
        return True
    return False


def shot_prompt(board: dict, shot: dict, aspect: str) -> str:
    chars = board["characters"]
    cast = "; ".join(f"{name.split('_')[0]} = {chars[name]['description']}" for name in shot["characters"])
    framing = "vertical 9:16 composition" if aspect == "9:16" else "horizontal 16:9 widescreen composition"
    if aspect == "16:9":
        lead = "The same scene, same people, same light and same moment as the last reference image, recomposed as a wide frame. "
    else:
        lead = ""
    parts = [lead + shot["keyframe_prompt"]]
    if cast:
        parts.append("Characters (match the reference images exactly): " + cast)
    parts.append(framing)
    parts.append(shot.get("style_override") or board["style_block"])
    return ". ".join(parts)


def run(board: dict | None = None, only: set[str] | None = None) -> int:
    board = board or load_storyboard()
    made = 0
    # 1. Reference sheet: base characters first, then derived ones.
    chars = board["characters"]
    order = sorted(chars, key=lambda n: 1 if chars[n].get("derived_from") else 0)
    for name in order:
        c = chars[name]
        refs = [reference_path(c["derived_from"])] if c.get("derived_from") else []
        prompt = c["sheet_prompt"] + ". " + board["style_block"]
        made += _make(f"ref:{name}", reference_path(name), prompt, SIZES["ref"], c["seed"], refs, board)
    # 2. Keyframes, vertical first, then horizontal conditioned on the vertical.
    for shot in board["shots"]:
        sid = shot["shot_id"]
        if only and sid not in only:
            continue
        refs = [reference_path(n) for n in shot["characters"]]
        v = keyframe_path(sid, "9:16")
        made += _make(f"{sid}.v", v, shot_prompt(board, shot, "9:16"), SIZES["9:16"], shot["seed"], refs, board)
        if "16:9" in board["aspect_ratios"]:
            h = keyframe_path(sid, "16:9")
            made += _make(f"{sid}.h", h, shot_prompt(board, shot, "16:9"), SIZES["16:9"], shot["seed"], refs + [v], board)
    total = len(chars) + len(board["shots"]) * len(board["aspect_ratios"])
    print(f"keyframes: {made} generated, {total - made} cached -> {rel(KEY_DIR)}")
    return made


if __name__ == "__main__":
    run()
