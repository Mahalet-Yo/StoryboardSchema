"""Smoke test: one cheap call per provider, each logged to runs.jsonl, before spending real quota.

TTS is not called here on purpose: the free tier allows only a handful of TTS requests a day
(FAILURES.md F2), so the smoke test checks the key with a text model instead.
"""

from __future__ import annotations

import base64
import time

import requests

from ..common import PermanentError, call_with_retry, classify_http, ffmpeg, require_env


def _gemini_text():
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
    resp = requests.post(url, headers={"x-goog-api-key": require_env("GEMINI_API_KEY")},
                         json={"contents": [{"parts": [{"text": "Reply with the single word: ready"}]}]}, timeout=60)
    if not resp.ok:
        raise classify_http(resp.status_code, resp.text)
    return resp.json(), {}, None


def _flux():
    url = (f"https://api.cloudflare.com/client/v4/accounts/{require_env('CLOUDFLARE_ACCOUNT_ID')}"
           "/ai/run/@cf/black-forest-labs/flux-2-klein-4b")
    resp = requests.post(url, headers={"Authorization": f"Bearer {require_env('CLOUDFLARE_API_TOKEN')}"},
                         files={"prompt": (None, "a clay coffee pot, warm light"), "width": (None, "256"),
                                "height": (None, "256"), "seed": (None, "1")}, timeout=120)
    if not resp.ok:
        raise classify_http(resp.status_code, resp.text)
    return len(base64.b64decode(resp.json()["result"]["image"])), {}, None


def _ace_space():
    from gradio_client import Client

    Client("ACE-Step/Ace-Step-v1.5", verbose=False).view_api(return_format="dict", print_info=False)
    return True, {}, None


def run() -> None:
    checks = [("gemini", "gemini-3.5-flash-lite", _gemini_text), ("cloudflare", "@cf/black-forest-labs/flux-2-klein-4b", _flux),
              ("hf-space", "ACE-Step/Ace-Step-v1.5 (reachability)", _ace_space)]
    for provider, model, fn in checks:
        t0 = time.perf_counter()
        try:
            call_with_retry(fn, stage="smoke", artifact=provider, provider=provider, model=model, params={},
                            seed=None, input_hash=None, attempts=2)
            print(f"  {provider:<11} ok   {time.perf_counter() - t0:5.1f}s  {model}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {provider:<11} FAIL {time.perf_counter() - t0:5.1f}s  {model}: {str(exc)[:120]}")
    filters = ffmpeg(["-filters"], capture=True)
    missing = [f for f in ("ass", "sidechaincompress", "loudnorm", "zoompan") if f" {f} " not in filters]
    print(f"  ffmpeg      {'ok' if not missing else 'MISSING ' + str(missing)}")
    if missing:
        raise PermanentError(f"FFmpeg lacks filters {missing}")
