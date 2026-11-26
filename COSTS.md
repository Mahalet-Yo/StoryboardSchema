# Costs

<!-- generated:start -->
| Stage | Provider | Model | OK calls | Failed / retried | Mean latency (s) | Total time (s) | GPU min | List-price equivalent (USD) | Real spend |
|---|---|---|---|---|---|---|---|---|---|
| assemble | local | ffmpeg-export | 2 | 0 | 70.5 | 141.0 | 0 (CPU) | 0 (local) | $0 |
| assemble | local | ffmpeg-mix | 1 | 0 | 17.2 | 17.2 | 0 (CPU) | 0 (local) | $0 |
| keyframes | cloudflare | @cf/black-forest-labs/flux-2-klein-4b | 26 | 5 | 12.2 | 317.3 | 0 | 0.0430 | $0 |
| music | hf-space | ACE-Step 1.5 (xl-turbo) | 0 | 1 | 0.0 | 0.0 | 0 | n/a | $0 |
| music | local | synth-tezeta-v1 | 3 | 0 | 3.8 | 11.3 | 0 (CPU) | 0 (local) | $0 |
| narration | gemini | gemini-3.8-flash-lite-tts | 8 | 1 | 3.9 | 31.2 | 0 | 0.0076 | $0 |
| shots | local | ffmpeg-zoompan | 16 | 0 | 7.6 | 121.0 | 0 (CPU) | 0 (local) | $0 |

List-price total for every logged call: **$0.0506**. Real spend: **$0** (free tiers and a CPU laptop).
<!-- generated:end -->
