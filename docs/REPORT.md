# Report: The Blessings of Pure Hands

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

**Test 2 (near-final cut).** Three people from the audience watched the vertical cut on a phone. All three:
- could say what the film is about ("the relationship, love and respect between an Ethiopian father and daughter");
- felt "the emotion the girl feels";
- saw the girl and the woman as one person;
- could follow the story with the sound off;
- did not find the music too loud, which confirmed the measured ducking choice by ear.

Two things did not work:
- **They wanted to see her face first** instead of the hands. I changed shot 1 to a profile of her face as she pours (DESIGN.md §6, EXPERIMENTS E14). It took two tries: the first image fused the oil lamp and the pitcher.
- **Pronunciation in shot 3, and around 9 s (shot 2), plus a comment that the narrator "doesn't sound fluent."** Shot 3's line seems to have a plural subject with a singular verb (ቃላቶች … አደገ), and shot 2 spells God two ways. Both text fixes are written, but I could not re-voice them: both Gemini TTS models had hit their daily free quota (FAILURES F11). The pictures now work for this audience; the voice is the weak link, and it is the first thing I would redo.

What surprised me was where the criticism landed. I had spent most of my effort on the pictures, on keeping the family consistent and getting past the image filter, and none of the viewers complained about them. Every problem they raised was about the voice and about seeing the daughter's face. People connect to a story through a face and a voice they trust. The film needed her face from the first second, and an Amharic voice that sounds like someone's sister, not a reader.

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
- **The same line in Tigrinya and Afaan Oromo** (E13). TTS did *not* refuse Oromo, although it is off the language list. The weak spot was translation: the Tigrinya keeps Amharic verb forms, and the overloaded Flash models pushed the work to Flash-Lite (F10). Length matters too: Oromo ran 1.44× the Amharic, and the narration-driven timeline absorbs it. A native Tigrinya or Oromo speaker has not listened to the two clips yet, so whether they are understandable is still an open question. I have recorded it as pending in EXPERIMENTS.md rather than guess.
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

## 7. Why this story

I chose this story because in Ethiopian families a parent's blessing (*mirkat*) is not just words at a doorway. It is something people carry for the rest of their lives, and it can stay meaningful long after the parent is gone. I wanted a film that someone could send to their own father or mother.

What I will remember from building it is that the model calls were the easy part. The work was everything around them: a contract the whole pipeline agrees on, a log that tells the truth about what happened, a cache that makes a one-line change cheap, and the habit of asking real people early. The models will be replaced in a few months; that way of working is what I take into the next project.
