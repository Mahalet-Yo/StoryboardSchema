"""Stage logic that needs no network: timeline, subtitles, music composer, Ken Burns render, keyframe prompts."""

import io
import wave

import pytest
from PIL import Image

from pipeline import assemble, common, keyframes, music, shots, timeline


def _speech(board, seconds):
    return {s["shot_id"]: seconds for s in board["shots"]}


def test_narration_sets_shot_length(board, tmp_path, monkeypatch):
    monkeypatch.setattr(timeline, "OUTPUTS", tmp_path)
    speech = _speech(board, 2.0)
    speech["shot_02"] = 12.0
    tl = timeline.build(board, speech)
    shot2 = next(s for s in tl["shots"] if s["shot_id"] == "shot_02")
    assert shot2["stretched"] and shot2["duration"] >= timeline.LEAD_S + 12.0 + timeline.TAIL_S
    assert all(abs(s["duration"] * 24 - round(s["duration"] * 24)) < 0.01 for s in tl["shots"])


def test_timeline_refuses_a_film_over_90_seconds(board, tmp_path, monkeypatch):
    monkeypatch.setattr(timeline, "OUTPUTS", tmp_path)
    with pytest.raises(common.PermanentError):
        timeline.build(board, _speech(board, 14.0))


@pytest.mark.parametrize("aspect", ["9:16", "16:9"])
def test_subtitles_never_exceed_two_lines(board, tmp_path, monkeypatch, aspect):
    monkeypatch.setattr(timeline, "OUTPUTS", tmp_path)
    tl = timeline.build(board, _speech(board, 5.0))
    wrap = assemble.WRAP[aspect]
    for start, end, text in assemble.subtitle_events(board, tl, wrap):
        lines = text.split("\\N")
        assert len(lines) <= 2 and all(len(x) <= wrap for x in lines) and end > start


def test_srt_timestamps():
    assert assemble._ts(61.5, True) == "00:01:01,500"


def _tiny_timeline():
    return {"total": 6.0, "cues": [{"id": "memory", "start": 0.0}, {"id": "resolution", "start": 3.0}]}


def test_music_composer_is_deterministic_per_seed():
    a = music.compose(7, _tiny_timeline(), 66)
    assert a == music.compose(7, _tiny_timeline(), 66)
    assert a != music.compose(8, _tiny_timeline(), 66)
    with wave.open(io.BytesIO(a)) as w:
        assert w.getnchannels() == 2 and w.getnframes() / w.getframerate() >= 6.0


def test_voice_band_metric_is_a_fraction():
    share = music.voice_band_share(music.compose(1, _tiny_timeline(), 66))
    assert 0.0 < share < 1.0


def test_ken_burns_render_has_exact_length(tmp_path):
    src = tmp_path / "k.png"
    Image.new("RGB", (768, 1344), (120, 80, 40)).save(src)
    out = tmp_path / "c.mp4"
    shots.render(src, out, "push_in", 1.0, "9:16", 24)
    assert abs(common.media_duration(out) - 1.0) < 0.05


def test_keyframe_prompt_carries_style_and_character_wording(board):
    shot = next(s for s in board["shots"] if s["characters"])
    prompt = keyframes.shot_prompt(board, shot, "9:16")
    assert board["style_block"] in prompt
    for name in shot["characters"]:
        assert board["characters"][name]["description"] in prompt
    assert "same scene" in keyframes.shot_prompt(board, shot, "16:9")
