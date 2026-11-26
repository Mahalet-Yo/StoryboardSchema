"""Cache, retries, quota handling and log redaction."""

import json

import pytest

from pipeline import common
from pipeline.common import PermanentError, TransientError


def test_cache_is_fresh_only_for_the_same_inputs(tmp_path):
    out = tmp_path / "a.bin"
    common.write_artifact(out, b"hello", "hash-1", {"x": 1})
    assert common.is_fresh(out, "hash-1")
    assert not common.is_fresh(out, "hash-2")


def test_an_altered_artifact_is_not_fresh(tmp_path):
    out = tmp_path / "a.bin"
    common.write_artifact(out, b"hello", "hash-1", {})
    out.write_bytes(b"edited by hand")
    assert not common.is_fresh(out, "hash-1")


def test_input_hash_ignores_key_order():
    assert common.compute_hash({"a": 1, "b": 2}) == common.compute_hash({"b": 2, "a": 1})


def test_transient_errors_are_retried_and_every_attempt_logged(runlog, monkeypatch):
    monkeypatch.setattr(common.time, "sleep", lambda s: None)
    calls = iter([TransientError("503"), TransientError("timeout"), ("ok", {"n": 1}, 0.01)])

    def fn():
        r = next(calls)
        if isinstance(r, Exception):
            raise r
        return r

    res = common.call_with_retry(fn, stage="t", artifact="a", provider="p", model="m", params={}, seed=1,
                                 input_hash="h")
    assert res.value == "ok" and res.attempts == 3
    lines = [json.loads(x) for x in runlog.read_text().splitlines()]
    assert [x["status"] for x in lines] == ["retry", "retry", "ok"]
    assert {"model", "params", "seed", "latency_s", "cost_usd"} <= set(lines[-1])


def test_permanent_errors_stop_at_once(runlog):
    def fn():
        raise PermanentError("HTTP 400")

    with pytest.raises(PermanentError):
        common.call_with_retry(fn, stage="t", artifact="a", provider="p", model="m", params={}, seed=None,
                               input_hash=None)
    assert len(runlog.read_text().splitlines()) == 1


def test_daily_quota_429_is_not_retried():
    body = '{"error":{"message":"limit: 10 requests per day. Please retry in 15h15m39s"}}'
    assert isinstance(common.classify_http(429, body), PermanentError)


def test_per_minute_429_is_retried_with_its_wait():
    err = common.classify_http(429, '{"error":{"message":"3 requests per minute"}}', "20")
    assert isinstance(err, TransientError) and err.retry_after == 20


def test_secrets_are_redacted_from_logs(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFAKEFAKEFAKE1234")
    assert "AIzaFAKE" not in common.redact("key=AIzaFAKEFAKEFAKE1234 failed")
    fake_token = "gh" + "p_" + "x" * 32  # built at runtime so the secrets scan does not flag this file
    assert "<redacted>" in common.redact(f"token {fake_token}")
