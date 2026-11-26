"""Nothing secret is committed, and every logged model call carries the fields the brief asks for."""

import json
import re
import subprocess

from pipeline.common import ROOT, RUNS_LOG

SECRET = re.compile(r"(AIza[0-9A-Za-z_\-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}|Bearer [A-Za-z0-9_\-]{30,})")


def _tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for name in out.splitlines():
        if name.endswith((".py", ".json", ".jsonl", ".md", ".yml", ".yaml", ".toml", ".txt", ".cfg", ".example",
                          "Makefile", "Dockerfile")):
            yield ROOT / name


def test_no_secrets_in_tracked_files():
    leaks = [str(p) for p in _tracked_text_files() if p.exists() and SECRET.search(p.read_text(errors="ignore"))]
    assert not leaks, f"possible secret in {leaks}"


def test_env_file_is_ignored():
    res = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT)
    assert res.returncode == 0


def test_run_log_lines_have_the_required_fields():
    required = {"model", "params", "seed", "latency_s", "cost_usd", "status", "stage"}
    for line in RUNS_LOG.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        assert required <= set(entry), entry
