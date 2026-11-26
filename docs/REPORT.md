# Report: The Blessings of Pure Hands

*Draft built from the repository's evidence. Text in [brackets] has to come from you: the second user test and your own voice. Export to PDF/Word, or submit this file's link.*

## 1. What I set out to make, and for whom

An 81-second film in Amharic with English subtitles, about a custom many Ethiopian families know: a child washes a parent's feet and receives a *mirkat*, a blessing. A daughter washes her father's feet and hears him bless her. Years later, after his death, she lives the life he blessed her into.

The audience is Ethiopians at home and in the diaspora who grew up with parental blessings, watching on a phone, often with the sound off. The intended feeling at the end is that a parent's blessing doesn't end with the parent (DESIGN.md §1).

The pipeline is the real product. One file, `storyboard.json`, drives five stages, and `make film` regenerates both MP4s from it. A clean clone makes no model calls, because the paid-for outputs and their cache records are committed.

## 2. What I learned from my audience

**Test 1 (radio cut).** Three people from the audience liked the story and related to it, but said the words were not yet strong enough. We revised five of the eight Amharic lines (commit `2afb02c`, table in DESIGN.md §4):
- The first line moved from "*his* heart filled with pure blessings" to "*my* heart filled with so many blessings": the blessing belongs to the daughter.
- The father's blessing became the words fathers actually say ("may God go before you on your path, may He raise you in wisdom and understanding").
- "Planted" became "sown", setting up the harvest in shot 5.
- The father in heaven became present tense ("his heart fills with joy"): he is still watching.

**Test 2 (near-final cut).** [Who watched, on what device. What each said to the protocol questions in DESIGN.md §6. Especially: did the girl and the woman read as one person, and did any Amharic word sound wrong? Then name the storyboard change and its commit id, or say why nothing changed.]

## 3. The hardest problem and how I solved it

Getting a consistent, recognisably Ethiopian family on screen from a free image API whose safety filter kept refusing a respectful family ritual.
- **Ethnicity drift (E1).** The first reference sheet came back Mediterranean. The fix was describing the qualities (dark brown skin, East African features, shuruba braids, the tibeb border) instead of trusting the word "Ethiopian".
- **The filter (F3).** It refused 6 of 35 image calls, all involving the child, and the adult daughter once. Three changes got around it:
  - A change in the plan (E4): shot 1 became an insert of hands and water. It's also a better opening: the ritual before the faces.
  - A change in the conditioning (E2): an adult is never conditioned on a child's image. Continuity across the age jump comes from shared wording and the tibeb border at both ages.
  - A change in the code (E5): I discovered the filter is *not deterministic* (the identical shot_01.h request was refused, then accepted 23 s later). The keyframe stage now retries a flagged output with derived seeds and records the seed it actually used.
- **Cross-ratio consistency (E6).** Conditioning each 16:9 frame on its 9:16 sibling keeps the same set and light. Without it, shot 5's courtyard changed its paving, trees and sky.

## 4. A suggested practice that beat my instinct, and one that did not

**Beat my instinct: the suggested ducking setting (E8).** I expected the brief's 0.02 / 6 / 300 ms / 1500 ms to swallow a quiet score and wanted something gentler. I measured instead of arguing. On the real stems, the suggested setting lowered the music 11.5 dB under speech and lost only 0.4 dB in the pauses; my gentler setting reached only 4.8 dB. I adopted the brief's setting (`outputs/experiments/duck_sweep.json`).

**Did not survive contact: "make the score with ACE-Step on a free GPU" (F4), and image-to-video with Wan 2.2 (F5).** With no GPU and no Kaggle token, I tried the hosted ACE-Step Spaces. One was never initialised, the init endpoint rejected its own default, the older Space no longer existed, and the anonymous ZeroGPU quota (180 s a day) was exhausted by a single request. The fallback held:
- a seeded composer in NumPy, with krar-like plucks in the tezeta mode, structured by the storyboard's spotting cues;
- eased Ken Burns moves chosen per shot.

The lesson isn't that the practice is wrong. A pipeline built around one hosted model needs a deterministic fallback for when that model isn't there, and that fallback must be labelled honestly (the end card says "Score: generated in code").

## 5. Curiosity beyond the floor

- **Measured ducking instead of tuning by ear** (E8, `make duck-sweep`): a reusable tool that measures any setting on your own stems.
- **A probe of the safety filter's determinism** (E5): the finding changed the code.
- **A score composer in the tezeta mode**, Ethiopia's mode of nostalgia, driven by spotting cues: an open, deterministic alternative to a hosted music model.
- **The same line in Tigrinya and Afaan Oromo** (E13). TTS did *not* refuse Oromo, although it is off the language list. The weak spot was translation: the Tigrinya keeps Amharic verb forms, and the overloaded Flash models pushed the work to Flash-Lite (F10). Length matters too: Oromo ran 1.44× the Amharic, and the narration-driven timeline absorbs it. [Add the native speakers' verdict.]
- **A tool others can use:**
  - the CLI (`python -m pipeline`);
  - a Docker image;
  - CI that validates the contract and runs 27 offline tests;
  - `AGENTS.md` plus a `regenerate-shot` skill, so someone else's coding agent can change a shot and prove only that shot was regenerated.

## 6. What I would build next

1. A Kaggle worker for Wan 2.2 at `shots.render`, keeping Ken Burns as its fallback, and a measured GPU-minutes column in COSTS.md.
2. ACE-Step with a Hugging Face token, auditioned blind against the tezeta composer with five listeners.
3. The same film in Tigrinya and Afaan Oromo. FAILURES.md would document exactly where TTS fails; Oromo is not on the TTS language list.
4. A small web form where a relative tells their story and the pipeline drafts a storyboard for a person to approve.

[Close in your own words: why this story, and what you'll remember from building it.]
