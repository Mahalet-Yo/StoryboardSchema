# Architecture

```
                        ┌──────────────── storyboard.json (the contract) ────────────────┐
                        │   validated by schema/ + cross-checks before every command      │
                        └───────────────────────────────┬─────────────────────────────────┘
                                                        │
       ┌────────────────────┬───────────────────────────┼──────────────────────┐
       ▼                    ▼                           ▼                      ▼
  narration            keyframes                     music                 (timeline)
  Gemini TTS     reference sheet → 9:16 → 16:9   ACE-Step Space → synth    measured speech
  one WAV/shot      FLUX.2 klein (Workers AI)      3 seeded candidates     sets shot length
       │                    │                           │                      │
       └──────────┬─────────┴──────────────┬────────────┴──────────────────────┘
                  ▼                        ▼
              timeline.json  ──────►   shots (Ken Burns, FFmpeg)  ──►  assemble (FFmpeg)
                                                                        mix · duck · loudnorm
                                                                        subtitles · end card
                                                                        9:16 + 16:9 · QC
                                                                              │
                                                     outputs/final/film.{vertical,horizontal}.mp4
```

## Stages and contracts

Every stage reads `storyboard.json` and writes files under `outputs/`. No stage talks to another stage directly; the only thing passed between them is files on disk plus `outputs/timeline.json`.

| Stage | Module | Reads from the storyboard | Writes | Model / tool |
|---|---|---|---|---|
| validate | `common.load_storyboard` | everything | nothing (fails fast) | JSON Schema + cross-checks |
| narration | `pipeline/narration.py` | `shots[].narration_am`, `narration_take`, `providers.tts` | `outputs/narration/<shot>.wav` | Gemini 3.8 Flash-Lite TTS (fallback: Flash TTS) |
| timeline | `pipeline/timeline.py` | `shots[].duration_sec`, `end_card`, `music.cues` + measured speech | `outputs/timeline.json` | none |
| keyframes | `pipeline/keyframes.py` | `characters`, `style_block`, `shots[].keyframe_prompt/seed/characters`, `providers.image` | `outputs/references/<character>.png`, `outputs/keyframes/<shot>.{v,h}.png` | FLUX.2 klein 4B on Cloudflare Workers AI |
| music | `pipeline/music.py` | `music.*`, `providers.music` | `outputs/music/score.seed<N>.wav`, `candidates.json` | ACE-Step 1.5 (HF Space), else the seeded synth composer |
| shots | `pipeline/shots.py` | `shots[].camera_move` + timeline | `outputs/clips/<shot>.{v,h}.mp4` | FFmpeg `zoompan` |
| assemble | `pipeline/assemble.py` | `mix`, `end_card`, `shots[].narration_en` + all of the above | `outputs/final/film.{vertical,horizontal}.mp4`, `outputs/subtitles/film.en.srt`, `qc.json` | FFmpeg |

Prompts, seeds, models, voice, mix settings and the end-card text all live in the storyboard, never in code. Changing the film means editing one JSON file.

**Validation** has two layers. The JSON Schema checks shape: types, enums, required fields, and that every shot has a `reason`. The cross-checks in `common.cross_check` cover what a schema can't express: every character a shot uses exists, every character has a consent/fictional record (the grading gate), shot ids are unique, and the planned length is 60–90 s. Once speech has been measured, `timeline.build` checks the real length again.

## Timing: the voice sets the cut

Professionals cut picture to the voice track, so the timeline does the same. Each shot lasts `max(duration_sec, 0.7 s lead + measured speech + 1.1 s tail)`, rounded up to a whole frame at 24 fps. In the current film, shots 2, 4 and 5 are stretched by their narration, which takes the film from 75 s planned to 81.25 s (`outputs/timeline.json`). Music cues are pinned to the start time of their `from_shot`, so the score's texture changes when the story does.

## Caching: a re-run only redoes what changed

Every artifact has a sidecar `<file>.meta.json` holding:
- `input_hash`: SHA-256 of everything that determines the file (prompt, seed, model, size, and the content hash of any input file);
- `output_hash`: the hash of the file itself, so a file edited by hand is treated as stale;
- the inputs in readable form, the run id and any extra facts (for example `seed_used`).

`is_fresh(artifact, input_hash)` is the only cache rule. Dependencies chain through content hashes:

```
character reference ──► every keyframe showing that character ──► its 16:9 sibling ──► its clips ──► the exports
narration line ──► timeline (if its length changes) ──► clips of stretched shots, mix ──► the exports
```

Example from `runs.jsonl` (run `20261126T202007-6196`): changing shot 8's keyframe prompt made exactly 2 model calls (shot_08.v and shot_08.h), re-rendered 2 clips, rebuilt the mix and re-exported. The other 17 images, 8 narration lines and 14 clips came from the cache.

What is deliberately **not** in a hash:
- **The TTS model name.** A line made by the fallback TTS model stays valid when the primary model comes back, so a quota problem never forces new performances.
- **The derived seed used after a filter flag.** The hash uses the storyboard seed, and the seed actually used is recorded in the sidecar as `seed_used`.

Writes are atomic (`*.tmp` then `os.replace`), so a crash never leaves a half-written file that looks fresh.

## Failure handling

| Failure | Detected as | Response |
|---|---|---|
| 5xx, 408, timeouts, connection errors | `TransientError` | retry with exponential backoff (4 s, 8 s, 16 s), up to 4 attempts, honouring `Retry-After` |
| 429 per-minute limit | `TransientError` with the server's wait | wait as told (capped at 90 s) and retry. Real case: narration shot_06 waited 54 s and succeeded |
| 429 daily quota ("retry in 15h…") | `PermanentError` | no pointless retries; narration moves to the next TTS model in `fallback_models` |
| Provider output filter ("output has been flagged") | `PermanentError` containing `flagged` | retry with deterministic derived seeds `seed+1000`, `seed+2000`; `seed_used` recorded |
| ACE-Step Space down or out of ZeroGPU quota | any exception | log it, then use the deterministic synth composer for this run |
| Film outside 60–90 s, unknown character, missing consent | `PermanentError` at validation | stop before any model is called |
| Anything else | exception | stop. Earlier artifacts remain cached, so the next run resumes where this one stopped |

Every attempt, successful or not, is one line in `runs.jsonl`. Each line records the stage, artifact, provider, model, params, seed, input hash, attempt number, status, latency, GPU minutes, units, cost and list price, plus the error with secrets redacted. Local FFmpeg renders are logged too, with `provider: "local"`, so `COSTS.md` can show time per stage.

## Audio chain (assemble)

1. **Narration stem:** each line is placed at its shot's `speech_start` with `adelay`, then two-pass `loudnorm` to `mix.narration_lufs` (−16).
2. **Music stem:** the selected score is trimmed to the film, levelled to `mix.music_lufs` (−16), offset by `music_gain_db` (−6 dB), then faded in over 2.5 s and out over 4 s.
3. **Ducking:** `sidechaincompress` with the voice as sidechain, using the settings in `mix.duck` (0.02 / 6 / 300 ms / 1500 ms, chosen by measurement: EXPERIMENTS.md E8).
4. **Master:** voice and ducked music are summed, then two-pass `loudnorm` to −14 LUFS with true peak at `true_peak_db − 0.7`. The extra 0.7 dB is headroom for the AAC encoder (E9).
5. **QC:** `ebur128` on the exported MP4s. The current result is −14.4 LUFS and −1.5 dBTP, at 81.25 s, for both files.

## Picture chain

- **Keyframes:** 768×1344 (9:16) and 1344×768 (16:9).
- **Clips:** `shots.render` upscales each keyframe 1.5× before `zoompan` (removing the integer-rounding jitter of a slow zoom), then applies an eased (smoothstep) move to 1080×1920 or 1920×1080 at 24 fps.
- **Edit:** clips and the end card are concatenated. The ASS subtitles are burned in: at most two lines, the 9:16 version sitting 20% above the bottom edge to stay clear of phone-app buttons. Fades are 0.8 s.
- **Export:** H.264 CRF 19 + AAC 192 kbps, `+faststart`, with a "Made with AI" metadata comment. The end card is on screen for 3.5 s.

## Code layout

```
pipeline/
  common.py        paths, env, validation, cache, retry, run log, FFmpeg helpers
  narration.py     keyframes.py     music.py     timeline.py     shots.py     assemble.py
  __main__.py      CLI: python -m pipeline film|radio|validate|<stage>|smoke|costs
  tools/
    smoke.py       one cheap call per provider before spending quota
    costs.py       rebuilds the measured table in COSTS.md from runs.jsonl
    duck_sweep.py  experiment E8 on the real stems
tests/             27 offline tests, run in CI and inside the Docker image
```

## Swapping a model

A provider is one function that returns `(bytes, units, list_price)` and raises `TransientError` or `PermanentError`. To replace FLUX.2 klein with another image model, write a new `_generate` with the same signature and name the model in `providers.image.model`. Caching, retries and logging stay the same. Wan 2.2 would plug in at `shots.render`: same inputs (keyframe, `motion_prompt`, duration), same output (an MP4 of exact length). The `kenburns` path stays as its fallback.
