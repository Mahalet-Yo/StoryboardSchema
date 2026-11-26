# Costs

Real spend: **$0**. Everything ran on free tiers and a CPU laptop (8 cores, 15 GB RAM, no GPU). The table below is rebuilt from `runs.jsonl` by `make costs` (and at the end of every `make film`). "List-price equivalent" is what the same calls would cost on paid tiers at the prices below.

## Measured, per stage and model (all runs so far)

<!-- generated:start -->
| Stage | Provider | Model | OK calls | Failed / retried | Mean latency (s) | Total time (s) | GPU min | List-price equivalent (USD) | Real spend |
|---|---|---|---|---|---|---|---|---|---|
| assemble | local | ffmpeg-export | 11 | 0 | 67.9 | 746.4 | 0 (CPU) | 0 (local) | $0 |
| assemble | local | ffmpeg-mix | 3 | 0 | 16.5 | 49.5 | 0 (CPU) | 0 (local) | $0 |
| experiment | cloudflare | @cf/black-forest-labs/flux-2-klein-4b | 1 | 1 | 9.6 | 9.6 | 0 | 0.0018 | $0 |
| experiment | gemini | gemini-3.1-flash-lite | 2 | 0 | 1.3 | 2.5 | 0 | n/a | $0 |
| experiment | gemini | gemini-3.5-flash | 0 | 4 | 0.0 | 0.0 | 0 | n/a | $0 |
| experiment | gemini | gemini-3.8-flash | 0 | 11 | 0.0 | 0.0 | 0 | n/a | $0 |
| experiment | gemini | gemini-3.8-flash-lite-tts | 2 | 0 | 5.0 | 10.1 | 0 | 0.0036 | $0 |
| keyframes | cloudflare | @cf/black-forest-labs/flux-2-klein-4b | 51 | 15 | 12.0 | 610.8 | 0 | 0.0862 | $0 |
| music | hf-space | ACE-Step 1.5 (xl-turbo) | 0 | 2 | 0.0 | 0.0 | 0 | n/a | $0 |
| music | local | synth-tezeta-v1 | 6 | 0 | 3.8 | 22.5 | 0 (CPU) | 0 (local) | $0 |
| narration | gemini | gemini-3.8-flash-lite-tts | 8 | 2 | 3.9 | 31.2 | 0 | 0.0076 | $0 |
| narration | gemini | gemini-3.8-flash-tts | 8 | 2 | 5.6 | 44.8 | 0 | 0.0120 | $0 |
| shots | local | ffmpeg-zoompan | 38 | 0 | 7.5 | 283.6 | 0 (CPU) | 0 (local) | $0 |
| smoke | cloudflare | @cf/black-forest-labs/flux-2-klein-4b | 1 | 0 | 9.3 | 9.3 | 0 | n/a | $0 |
| smoke | gemini | gemini-3.5-flash-lite | 1 | 0 | 1.9 | 1.9 | 0 | n/a | $0 |
| smoke | hf-space | ACE-Step/Ace-Step-v1.5 (reachability) | 1 | 0 | 12.0 | 12.0 | 0 | n/a | $0 |

List-price total for every logged call: **$0.1111**. Real spend: **$0** (free tiers and a CPU laptop).
<!-- generated:end -->

## One clean film, end to end

What a full regeneration of the current film costs: 8 narration lines, 3 reference images, 16 keyframes, 3 score candidates, 16 clips, mix and 2 exports. Taken from the logged means above.

| Stage | Calls | Wall time | GPU minutes | List price |
|---|---|---|---|---|
| narration | 8 TTS | ~31 s (3.9 s each), plus up to 60 s of rate-limit waits at 3 requests/min | 0 | ~$0.008 |
| keyframes | 19 images | ~3.8 min (12.0 s each) | 0 | ~$0.027 (19 × ~156 neurons × $0.011/1k) |
| music | 3 synth (CPU) | ~11 s | 0 | $0 |
| shots | 16 Ken Burns clips (CPU) | ~2 min (7.6 s each) | 0 | $0 |
| assemble | mix + 2 exports (CPU) | ~2.5 min | 0 | $0 |
| **total** | **27 model calls** | **~9–10 min** | **0** | **≈ $0.035** |

A re-run with nothing changed makes **0 model calls** and takes about 8 s (`runs.jsonl`, run `20261126T202736-4921`). A one-shot keyframe edit makes 2 calls and takes about 3.5 minutes, nearly all of it FFmpeg re-exporting the two films (E12).

## Free-tier limits I actually hit (26 November 2026)

| Service | Limit found | How I found it |
|---|---|---|
| Gemini 3.8 Flash TTS | **10 requests/day**, free tier | 429 "retry in 15h15m" (FAILURES F2) |
| Gemini 3.8 Flash-Lite TTS | **3 requests/minute** (daily cap not reached: 10 requests used) | 429 with a 54 s wait, retried (F2) |
| Cloudflare Workers AI, FLUX.2 klein 4B | 10,000 neurons/day; 1 image at 768×1344 ≈ 6 tiles ≈ 156 neurons, so ~60 keyframes/day | dashboard/docs; 35 calls so far, no quota error |
| Cloudflare output filter | not a quota, but 6 of 35 image calls refused (17%) | F3, E5 |
| Hugging Face ZeroGPU (anonymous) | about 180 s of GPU per day; one ACE-Step request asks for 180 s | 429-style error "180s requested vs. 178s left" (F4) |
| Kaggle T4 ×2 | ~30 GPU h/week (brief) | not used: no account token on this machine (F4, F5) |

## List prices used

| Model | Price | Source |
|---|---|---|
| Gemini 3.8 Flash TTS | $0.50 / 1M text in, $9.00 / 1M audio out, 25 audio tokens per second | pricing pages as noted on 25 Nov 2026 in our reference notes; not re-checked tonight |
| Gemini 3.8 Flash-Lite TTS | $0.50 / 1M in, $6.00 / 1M audio out | same |
| FLUX.2 klein 4B (Workers AI) | 26.05 neurons per 512 px output tile, 5.37 per input tile, $0.011 / 1,000 neurons | Workers AI model page, same notes |
| Ken Burns, synth score, assembly | local CPU, no list price | — |

## What the GPU path would have cost (estimate, not measured)

Wan 2.2 TI2V-5B at 480p on a Kaggle T4 takes several minutes per 5 s clip (brief). Our 8 shots need ~81 s of picture, so 16–17 clips of 5 s each per aspect ratio, or about 1–2 GPU hours per full pass on the T4. That is 3–7% of a weekly Kaggle quota per pass. Our Ken Burns path took 2 CPU minutes. This number is an estimate from the brief, not a measurement, and it is the first thing I'd measure with a Kaggle token.

## Frontier comparison

No frontier lane (Omni Flash, Nano Banana, Lyria 3.5) was opened for this cohort, so there is no measured comparison. `gemini-nano-banana-2.1` appears in this key's model list, but it is behind paid billing, and I did not call it.
