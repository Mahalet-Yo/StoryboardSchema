import copy
import json

import pytest

from pipeline import common


@pytest.fixture
def board():
    """The real storyboard, deep-copied so a test can break it freely."""
    return copy.deepcopy(json.loads(common.STORYBOARD_PATH.read_text(encoding="utf-8")))


@pytest.fixture
def runlog(tmp_path, monkeypatch):
    """Send run-log lines to a temp file instead of the real runs.jsonl."""
    path = tmp_path / "runs.jsonl"
    monkeypatch.setattr(common, "RUNS_LOG", path)
    return path
