# Ethics: consent, licences, labelling, private data

## Consent record

| Who appears or is heard | Real person? | Basis | Record |
|---|---|---|---|
| The father (`characters.father`) | No. A composite, written from the custom of a father's blessing, not from one person | `fictional` | `storyboard.json` → `characters.father.consent`; his face is generated from text only |
| The daughter as a child (`daughter_child`) | No. A composite character | `fictional` | `characters.daughter_child.consent`. No photograph of any real child was used as a reference |
| The daughter as an adult (`daughter_adult`) | No. A composite character | `fictional` | `characters.daughter_adult.consent` |
| The narrator's voice | No. Gemini TTS prebuilt voice "Kore" | synthetic voice; no cloning | `providers.tts.voice` |

- No real person's face, likeness or voice was generated, and no voice was cloned. The film tells a story about a custom (washing a father's feet and receiving his blessing), told in the first person by a fictional daughter.
- The code enforces the consent record. `common.cross_check` refuses to run if any character used in a shot lacks a `consent.recorded` entry (`test_missing_consent_record_blocks_the_run`). Adding a real person later requires `basis: consent_on_file` and a written, dated consent, recorded below, *before* anything of them is generated.

**Template for a real person, if one is added:**

| Name | Relationship | What they agreed to (likeness / voice / words) | Date | How recorded |
|---|---|---|---|---|
| — | — | — | — | — |

## Licences

| Component | Used for | Licence / terms | Note |
|---|---|---|---|
| FLUX.2 klein 4B (Black Forest Labs) via Cloudflare Workers AI | reference sheet, keyframes | model: Apache 2.0 (4B); the hosted service is under Cloudflare's terms | the 9B klein is non-commercial; we deliberately use 4B |
| Gemini 3.8 Flash-Lite TTS (Google) | narration | Gemini API terms; free-tier inputs may be used to improve Google's products | no private family details sent, see below |
| Synth score (`pipeline/music.py`) | score | our own code, deterministic output, no third-party audio | no samples, no training data |
| ACE-Step 1.5 (attempted) | score | MIT; outputs usable commercially | not used in the final film (FAILURES F4) |
| FFmpeg (imageio-ffmpeg static build / Debian ffmpeg) | all assembly | LGPL/GPL build | a tool, not part of the output |
| DejaVu fonts | subtitles, end card | Bitstream Vera / DejaVu licence (free) | |
| Python libraries (requirements.txt) | pipeline | MIT / BSD / Apache 2.0 / HPND (Pillow) | |
| Amharic narration text | narration, subtitles | written for this film by the author | |

## Labelling plan

1. **In the film:** a 3.5 s end card in both aspect ratios says **"Made with AI"** and names the image, voice and score sources, and that the characters are fictional composites (`storyboard.json` → `end_card`).
2. **In the file:** the MP4 metadata comment says "Made with AI…". Nothing strips provider watermarks or provenance metadata; the pipeline only re-encodes.
3. **On the platform:** the post goes up with the platform's AI disclosure turned on (YouTube "altered or synthetic content", TikTok "AI-generated" label, Meta "AI info"). The caption also says the film was generated with AI.
4. **In the repository:** this file, the README and the run log state what generated each part.

## Style and identity

Prompts describe qualities (warm, 35 mm grain, soft window light, earth tones) and never name a living artist or a real person.

## Private data

Free-tier endpoints may use what is sent to them. The prompts and narration contain no names, places or private family details: the father and daughter are unnamed, and the village is "Ethiopian highlands". Keys live only in `.env`, which is git-ignored. Logs redact secrets, and a test scans every tracked file for key patterns (`tests/test_repo_hygiene.py`).

## Cultural care

The blessing quoted in shot 2 is a common Ethiopian Orthodox parental blessing, given in Amharic as the author wrote it. Shot 7 shows a luminous sky rather than a literal heaven, so the film stays reverent for viewers of any faith (shot reason in the storyboard). Native-speaker review of the Amharic narration is part of the user tests in DESIGN.md.
