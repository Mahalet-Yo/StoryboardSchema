"""The storyboard is the contract: it must validate, and the cross-checks must catch what JSON Schema cannot."""

import json

import jsonschema
import pytest

from pipeline import common


def _validate(board):
    schema = json.loads(common.SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(board, schema)
    return common.cross_check(board)


def test_committed_storyboard_is_valid():
    board = common.load_storyboard()
    assert 8 <= len(board["shots"]) <= 12


def test_every_shot_states_its_reason(board):
    del board["shots"][0]["reason"]
    with pytest.raises(jsonschema.ValidationError):
        _validate(board)


def test_unknown_character_is_caught(board):
    board["shots"][0]["characters"] = ["grandmother"]
    assert any("unknown character" in p for p in _validate(board))


def test_missing_consent_record_blocks_the_run(board):
    board["characters"]["father"]["consent"]["recorded"] = False
    assert any("consent" in p for p in _validate(board))


def test_film_outside_60_to_90_seconds_is_refused(board):
    for shot in board["shots"]:
        shot["duration_sec"] = 3
    assert any("outside 60-90" in p for p in _validate(board))


def test_duplicate_shot_ids_are_refused(board):
    board["shots"][1]["shot_id"] = board["shots"][0]["shot_id"]
    assert any("unique" in p for p in _validate(board))


def test_prompts_and_seeds_live_in_the_storyboard(board):
    for shot in board["shots"]:
        assert isinstance(shot["seed"], int)
        assert shot["keyframe_prompt"] and shot["motion_prompt"]
