# AI Content Generation

A pipeline that turns one storyboard file into a narrated, scored, subtitled short film in 9:16 and 16:9. Its first production is **The Blessings of Pure Hands**: an 81-second film in Amharic with English subtitles, about a daughter who washed her father's feet and carried his blessing through his death into her own life. All five stages (narration, keyframes, moving shots, music and assembly) read the same [`storyboard.json`](storyboard.json).

[![ci](https://github.com/Mahalet-Yo/ai-content-generation/actions/workflows/ci.yml/badge.svg)](https://github.com/Mahalet-Yo/ai-content-generation/actions/workflows/ci.yml)

| | |
|---|---|
| Film | `outputs/final/film.vertical.mp4` (9:16, 1080×1920) and `film.horizontal.mp4` (16:9, 1920×1080), 81.25 s, −14.4 LUFS, −1.5 dBTP ([qc.json](outputs/final/qc.json)) |
| Subtitles | burned in, plus [`outputs/subtitles/film.en.srt`](outputs/subtitles/film.en.srt) |
| Cost | **$0** on free tiers; ≈ $0.035 list-price equivalent per full regeneration ([COSTS.md](COSTS.md)) |
| Time | ~10 min for a full regeneration on a CPU laptop; ~8 s when nothing changed |

## Run it

You need Linux or macOS, Python 3.12+ and `make`. FFmpeg is optional: if there is none on the system, a static build is installed with the Python requirements.

```bash
git clone https://github.com/Mahalet-Yo/ai-content-generation.git && cd ai-content-generation
cp .env.example .env          # add a Gemini key (AI Studio) and a Cloudflare Workers AI token
make film                     # storyboard.json -> outputs/final/film.{vertical,horizontal}.mp4
```

`make film` creates the virtualenv, validates the storyboard and runs every stage. Each stage skips anything whose inputs haven't changed.

**Clean clone, no keys needed.** The paid-for model outputs (narration, reference sheet, keyframes and the chosen score) are committed together with their `.meta.json` cache records. A fresh clone running `make film` therefore makes **no model calls** and rebuilds the clips, mix and both films locally. Delete a file in `outputs/` (or change its storyboard entry) and only that piece is regenerated, which is when the keys are needed.

Tested on 26 Nov: a fresh `git clone` with no `.env`, then `make film`, gave `0 model call(s), 17 local render(s)` in 3 min 26 s, including creating the virtualenv. The re-rendered clips and mix were byte-identical to the committed run, so the two exports were still fresh from the cache. The local stages are deterministic.

With Docker:

```bash
docker build -t heritage-short .
docker run --rm --env-file .env -v "$PWD:/app" heritage-short film
```

## Commands

| Command | What it does |
|---|---|
| `make film` | the whole pipeline, from the storyboard to both MP4s, QC, and the COSTS.md table |
| `make radio` | narration + score over black: the Phase 1 prototype (`outputs/radio_cut.mp4`) |
| `make validate` | JSON Schema + cross-checks (unknown characters, missing consent, 60–90 s) |
| `make narration` / `keyframes` / `music` / `shots` / `assemble` | one stage on its own |
| `make smoke` | one cheap call per provider, logged, before spending real quota |
| `make costs` | rebuild the measured table in COSTS.md from `runs.jsonl` |
| `make duck-sweep` | experiment E8: measure ducking settings on the real stems |
| `make lang-test` | experiment E13: shot 2 translated and voiced in Tigrinya and Afaan Oromo |
| `make test` | 27 offline tests (also run in CI and inside the Docker image) |

## Change one shot

Edit one shot's `keyframe_prompt`, or a `narration_am` line, in `storyboard.json`, then run `make film`. The summary at the end lists this run's model calls. For a keyframe edit it shows two image calls (that shot's 9:16 and 16:9) and nothing else. See [EXPERIMENTS.md E12](EXPERIMENTS.md#e12-does-a-one-line-storyboard-edit-really-regenerate-only-that-shot) and the run log.

```
run 20261126T202007-6196: 2 model call(s), 5 local render(s), 210s wall clock
  keyframes  shot_08.v   @cf/black-forest-labs/flux-2-klein-4b  ok  10.518s
  keyframes  shot_08.h   @cf/black-forest-labs/flux-2-klein-4b  ok   9.276s
```

## How it works

```
storyboard.json ─validate─► narration (Gemini TTS) ─► timeline (speech sets shot length)
                         ├► keyframes (reference sheet → 9:16 → 16:9, FLUX.2 klein)
                         ├► music (ACE-Step Space → seeded tezeta synth fallback)
                         └► shots (Ken Burns, FFmpeg) ─► assemble: duck · loudnorm · subtitles · end card · 2 exports · QC
```

| Stage | Model | Where it runs |
|---|---|---|
| narration | Gemini 3.8 Flash-Lite TTS, voice "Kore" (fallback: Flash TTS) | Gemini API, free tier |
| keyframes | FLUX.2 klein 4B, conditioned on the reference sheet | Cloudflare Workers AI, free allowance |
| music | ACE-Step 1.5 when the hosted Space is up; otherwise our seeded tezeta-mode composer | HF Space / local CPU |
| shots | eased pan/zoom per `camera_move` | FFmpeg, local |
| assembly | sidechain ducking, two-pass loudnorm to −14 LUFS, ASS subtitles, end card | FFmpeg, local |

The details, including contracts, the caching chain and failure handling, are in [ARCHITECTURE.md](ARCHITECTURE.md).

## Repository

```
storyboard.json      the contract: shots, reasons, prompts, seeds, characters, narration, music cues, mix
schema/              JSON Schema for the storyboard (validated before every run)
pipeline/            one module per stage + common (cache, retry, log) + CLI + tools
tests/               offline tests: contract, cache, retries, quota handling, timeline, subtitles, render, secrets
runs.jsonl           one line per model call attempt (model, params, seed, latency, cost, status)
outputs/             generated media + .meta.json cache records, kept so the run can be inspected
DESIGN.md            audience, intent, shot reasons, the two user tests and what changed
ARCHITECTURE.md      stages, contracts, caching, failure handling
EXPERIMENTS.md       14 hypothesis → change → result entries
FAILURES.md          what broke, what I tried, what fixed it
COSTS.md             measured latency per stage, limits hit, list-price equivalents
ETHICS.md            consent record, licences, labelling plan
AGENTS.md            how a coding agent works in this repo
docs/                report, walkthrough script, post draft
```

## Honest status

- **Moving shots:** Ken Burns pans over keyframes, not Wan 2.2 video. There was no GPU or Kaggle token on this machine ([FAILURES F5](FAILURES.md)).
- **Score:** generated by our own seeded composer, because both ACE-Step Spaces were down or out of ZeroGPU quota ([F4](FAILURES.md)).
- **Second user test:** done with three viewers ([DESIGN.md §6](DESIGN.md)). Shot 1 was changed to show her face. Two pronunciation fixes are written but not re-voiced, because both TTS models were out of daily quota ([F11](FAILURES.md)).

## Licence and labelling

Characters are fictional composites, and the voice is a stock TTS voice; no real person's likeness or voice is used. The film ends with a "Made with AI" card, and the post is published with the platform's AI label switched on. Licences of every model and output are listed in [ETHICS.md](ETHICS.md).
