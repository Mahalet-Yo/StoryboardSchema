"""Stage: assembly. Pure FFmpeg, deterministic: the same inputs give the same film.

1. narration stem: each line placed at its shot's speech_start, levelled to mix.narration_lufs
2. music stem: selected score trimmed to the film, levelled to mix.music_lufs, faded in and out
3. ducking: sidechaincompress, the voice drives a compressor on the music (settings in storyboard.mix)
4. master: voice + ducked music, two-pass loudnorm to mix.target_lufs / mix.true_peak_db
5. picture: shot clips + end card, English subtitles burned in (ASS, inside the vertical safe area)
6. export: H.264 + AAC MP4 per aspect ratio, plus an .srt sidecar and qc.json
"""

from __future__ import annotations

import json
import re
import textwrap
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import OUTPUTS, ROOT, compute_hash, ffmpeg, file_hash, is_fresh, load_storyboard, log_run, rel, seal
from .keyframes import aspect_tag
from .music import selected_path
from .narration import narration_path
from .shots import OUT_SIZE, clip_path

AUDIO_DIR = OUTPUTS / "audio"
SUB_DIR = OUTPUTS / "subtitles"
FINAL_DIR = OUTPUTS / "final"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SR = 48_000


def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


# --------------------------------------------------------------------------- audio


def _loudnorm_measure(src: Path, i: float, tp: float) -> dict:
    err = ffmpeg(["-i", str(src), "-af", f"loudnorm=I={i}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                 capture=True)
    return json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)[-1])


def build_mix(board: dict, timeline: dict) -> tuple[Path, Path]:
    """Returns (master mix, narration-only stem)."""
    mix = board["mix"]
    total = timeline["total"]
    music = selected_path(board)
    lines = [(s["shot_id"], s["speech_start"]) for s in timeline["shots"]]
    inputs = {"lines": [[sid, start, file_hash(narration_path(sid))] for sid, start in lines],
              "music": file_hash(music), "mix": mix, "total": total}
    digest = compute_hash({"stage": "mix", **inputs})
    master, voice_stem = AUDIO_DIR / "master.wav", AUDIO_DIR / "narration_stem.wav"
    if is_fresh(master, digest) and voice_stem.exists():
        print("  mix: cached")
        return master, voice_stem
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    # 1. narration stem
    args: list[str] = []
    chains = []
    for k, (sid, start) in enumerate(lines):
        args += ["-i", str(narration_path(sid))]
        ms = int(round(start * 1000))
        chains.append(f"[{k}:a]aresample={SR},aformat=channel_layouts=stereo,adelay={ms}|{ms}[l{k}]")
    labels = "".join(f"[l{k}]" for k in range(len(lines)))
    fc = ";".join(chains) + f";{labels}amix=inputs={len(lines)}:normalize=0,apad=whole_dur={total},atrim=0:{total}[v]"
    raw_voice = AUDIO_DIR / "narration_raw.wav"
    ffmpeg([*args, "-filter_complex", fc, "-map", "[v]", "-ar", str(SR), str(raw_voice)])
    m = _loudnorm_measure(raw_voice, mix["narration_lufs"], -2)
    ffmpeg(["-i", str(raw_voice), "-af",
            f"loudnorm=I={mix['narration_lufs']}:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
            f"aresample={SR}", str(voice_stem)])

    # 2. music stem: trim, level, fades
    music_stem = AUDIO_DIR / "music_stem.wav"
    fade_out = max(0.0, total - 4.0)
    ffmpeg(["-stream_loop", "-1", "-i", str(music), "-af",
            f"atrim=0:{total},aresample={SR},aformat=channel_layouts=stereo,"
            f"loudnorm=I={mix['music_lufs']}:TP=-2:LRA=11,aresample={SR},volume={mix['music_gain_db']}dB,"
            f"afade=t=in:d=2.5,afade=t=out:st={fade_out}:d=4", "-t", str(total), str(music_stem)])

    # 3 + 4. duck the music under the voice, sum, then measure for the two-pass master
    d = mix["duck"]
    summed = AUDIO_DIR / "summed.wav"
    ffmpeg(["-i", str(voice_stem), "-i", str(music_stem), "-filter_complex",
            f"[0:a]asplit=2[voice][sc];"
            f"[1:a][sc]sidechaincompress=threshold={d['threshold']}:ratio={d['ratio']}:"
            f"attack={d['attack_ms']}:release={d['release_ms']}[ducked];"
            f"[voice][ducked]amix=inputs=2:normalize=0[out]", "-map", "[out]", "-ar", str(SR), str(summed)])
    m = _loudnorm_measure(summed, mix["target_lufs"], mix["true_peak_db"])
    ffmpeg(["-i", str(summed), "-af",
            f"loudnorm=I={mix['target_lufs']}:TP={mix['true_peak_db']}:LRA=11:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}:linear=true,aresample={SR}", "-ar", str(SR), str(master)])
    latency = time.perf_counter() - t0
    seal(master, digest, inputs, {"pre_master_lufs": m["input_i"]})
    log_run(stage="assemble", artifact="master.wav", provider="local", model="ffmpeg-mix",
            params={"duck": d, "target_lufs": mix["target_lufs"]}, seed=None, input_hash=digest, attempt=1,
            status="ok", latency_s=latency)
    print(f"  mix: master built in {latency:.1f}s (pre-master {m['input_i']} LUFS)")
    return master, voice_stem


# --------------------------------------------------------------------------- subtitles


def _chunks(text: str, limit: int = 80) -> list[str]:
    """Split a line into subtitle events of at most two 40-character lines, at natural pauses."""
    if len(text) <= limit:
        return [text]
    parts = re.split(r"(?<=[,;:.!?])\s+", text)
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + 1 + len(p) > limit:
            out.append(cur)
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        out.append(cur)
    final = []
    for c in out:  # a single clause longer than the limit: wrap by words
        final += textwrap.wrap(c, limit) if len(c) > limit else [c]
    return final


def _ts(t: float, srt: bool) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def subtitle_events(board: dict, timeline: dict) -> list[tuple[float, float, str]]:
    events = []
    by_id = {s["shot_id"]: s for s in board["shots"]}
    for s in timeline["shots"]:
        text = by_id[s["shot_id"]]["narration_en"]
        chunks = _chunks(text)
        start, span = s["speech_start"] - 0.1, s["speech_s"] + 0.5
        weights = [len(c) for c in chunks]
        t = start
        for c, w in zip(chunks, weights):
            dur = span * w / sum(weights)
            events.append((t, t + dur, "\\N".join(textwrap.wrap(c, 42))))
            t += dur
    return events


def write_subtitles(board: dict, timeline: dict) -> dict[str, Path]:
    SUB_DIR.mkdir(parents=True, exist_ok=True)
    events = subtitle_events(board, timeline)
    srt = SUB_DIR / "film.en.srt"
    srt.write_text("\n".join(f"{i}\n{_ts(a, True)} --> {_ts(b, True)}\n{t.replace(chr(92) + 'N', chr(10))}\n"
                             for i, (a, b, t) in enumerate(events, 1)), encoding="utf-8")
    paths = {"srt": srt}
    for aspect in board["aspect_ratios"]:
        w, h = OUT_SIZE[aspect]
        vertical = aspect == "9:16"
        size = 58 if vertical else 50
        margin_v = int(h * 0.20) if vertical else 64  # keep clear of phone UI at the bottom of vertical feeds
        margin_lr = 80 if vertical else 160
        head = textwrap.dedent(f"""\
            [Script Info]
            ScriptType: v4.00+
            PlayResX: {w}
            PlayResY: {h}
            WrapStyle: 0
            ScaledBorderAndShadow: yes

            [V4+ Styles]
            Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
            Style: Default,DejaVu Sans,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3.2,1.5,2,{margin_lr},{margin_lr},{margin_v},1

            [Events]
            Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
            """)
        body = "".join(f"Dialogue: 0,{_ts(a, False)},{_ts(b, False)},Default,,0,0,0,,{{\\fad(150,150)}}{t}\n"
                       for a, b, t in events)
        p = SUB_DIR / f"film.{aspect_tag(aspect)}.ass"
        p.write_text(head + body, encoding="utf-8")
        paths[aspect] = p
    return paths


# --------------------------------------------------------------------------- end card and picture


def end_card_image(board: dict, aspect: str) -> Path:
    w, h = OUT_SIZE[aspect]
    img = Image.new("RGB", (w, h), (14, 11, 9))
    d = ImageDraw.Draw(img)
    title, label, *rest = board["end_card"]["lines"]
    scale = w / 1080 if aspect == "9:16" else h / 1080
    y = h * 0.36
    for text, font, colour in ((title, _font(SERIF, int(64 * scale)), (236, 214, 170)),
                               (label, _font(SANS, int(54 * scale)), (255, 255, 255))):
        for line in textwrap.wrap(text, 24 if aspect == "9:16" else 40):
            tw = d.textlength(line, font=font)
            d.text(((w - tw) / 2, y), line, font=font, fill=colour)
            y += font.size * 1.35
        y += 30 * scale
    small = _font(SANS, int(30 * scale))
    y += 20 * scale
    for text in rest:
        for line in textwrap.wrap(text, 44 if aspect == "9:16" else 80):
            tw = d.textlength(line, font=small)
            d.text(((w - tw) / 2, y), line, font=small, fill=(190, 180, 165))
            y += small.size * 1.5
    out = FINAL_DIR / f"endcard.{aspect_tag(aspect)}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def export(board: dict, timeline: dict, aspect: str, master: Path, subs: Path) -> Path:
    fps = timeline["fps"]
    tag = aspect_tag(aspect)
    card = end_card_image(board, aspect)
    out = FINAL_DIR / f"film.{'vertical' if aspect == '9:16' else 'horizontal'}.mp4"
    clips = [clip_path(s["shot_id"], aspect) for s in timeline["shots"]]
    inputs = {"clips": [file_hash(c) for c in clips], "card": file_hash(card), "subs": file_hash(subs),
              "audio": file_hash(master), "timeline": timeline}
    digest = compute_hash({"stage": "export", "aspect": aspect, **inputs})
    if is_fresh(out, digest):
        print(f"  export {tag}: cached")
        return out
    t0 = time.perf_counter()
    end = timeline["end_card"]
    card_clip = FINAL_DIR / f"endcard.{tag}.mp4"
    ffmpeg(["-loop", "1", "-i", str(card), "-vf", f"fps={fps},format=yuv420p,fade=t=in:d=0.6",
            "-t", str(end["duration"]), "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(card_clip)])
    listing = FINAL_DIR / f"concat.{tag}.txt"
    listing.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in [*clips, card_clip]), encoding="utf-8")
    total = timeline["total"]
    vf = (f"ass={rel(subs)},fade=t=in:st=0:d=0.8,fade=t=out:st={total - 0.8}:d=0.8,format=yuv420p")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(master),
            "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", str(fps), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-t", str(total),
            "-metadata", "comment=Made with AI. Images FLUX.2 klein, voice Gemini TTS, score generated in code.",
            "-movflags", "+faststart", str(out)])
    latency = time.perf_counter() - t0
    seal(out, digest, {"aspect": aspect, "clips": [rel(c) for c in clips]})
    log_run(stage="assemble", artifact=out.name, provider="local", model="ffmpeg-export",
            params={"aspect": aspect, "fps": fps, "crf": 19}, seed=None, input_hash=digest, attempt=1,
            status="ok", latency_s=latency)
    print(f"  export {tag}: {rel(out)} in {latency:.1f}s")
    return out


# --------------------------------------------------------------------------- QC


def qc(board: dict, timeline: dict, films: list[Path]) -> dict:
    from .common import media_duration

    report = {"films": [], "checks": {}}
    for f in films:
        err = ffmpeg(["-i", str(f), "-af", "ebur128=peak=true", "-f", "null", "-"], capture=True)
        summary = err[err.rfind("Summary:"):]
        lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
        peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
        dur = media_duration(f)
        report["films"].append({"file": rel(f), "duration_s": round(dur, 2), "integrated_lufs": lufs,
                                "true_peak_dbtp": peak})
    mix = board["mix"]
    report["checks"] = {
        "duration_60_90": all(60 <= x["duration_s"] <= 90 for x in report["films"]),
        "loudness_within_1lu": all(abs(x["integrated_lufs"] - mix["target_lufs"]) <= 1 for x in report["films"]),
        "true_peak_ok": all(x["true_peak_dbtp"] <= mix["true_peak_db"] + 0.5 for x in report["films"]),
        "both_aspects": len(films) == len(board["aspect_ratios"]),
        "end_card": bool(board["end_card"]["lines"]),
        "subtitles": (SUB_DIR / "film.en.srt").exists(),
    }
    report["passed"] = all(report["checks"].values())
    (FINAL_DIR / "qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run(board: dict | None = None, timeline: dict | None = None) -> list[Path]:
    board = board or load_storyboard()
    if timeline is None:
        timeline = json.loads((OUTPUTS / "timeline.json").read_text(encoding="utf-8"))
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    master, _ = build_mix(board, timeline)
    subs = write_subtitles(board, timeline)
    films = [export(board, timeline, a, master, subs[a]) for a in board["aspect_ratios"]]
    report = qc(board, timeline, films)
    status = "PASSED" if report["passed"] else "FAILED " + str([k for k, v in report["checks"].items() if not v])
    print(f"assemble: {', '.join(rel(f) for f in films)} | QC {status}")
    return films


def radio_cut(board: dict, timeline: dict) -> Path:
    """Phase 1 prototype: the same narration and mix over black, for the first audience test."""
    master, _ = build_mix(board, timeline)
    out = OUTPUTS / "radio_cut.mp4"
    ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=24:d={timeline['total']}", "-i", str(master),
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])
    print(f"radio cut: {rel(out)} ({timeline['total']:.1f}s)")
    return out


if __name__ == "__main__":
    import os

    os.chdir(ROOT)
    run()
