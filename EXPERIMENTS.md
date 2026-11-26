# Experiments

Each entry has a hypothesis, the one thing changed, the result, and the evidence. Seeds stayed fixed unless the change was the seed itself. The evidence is in `runs.jsonl` (search by `artifact`), in the `.meta.json` sidecars, and in `outputs/experiments/`.

---

## E1. Naming the ethnicity explicitly keeps the characters Ethiopian
- **Hypothesis:** "Ethiopian man/girl" alone is not enough for FLUX.2 klein. The model will drift towards a generic "warm-toned" look unless skin tone and features are named.
- **Change:** the three character descriptions and sheet prompts gained "Habesha Ethiopian … dark brown skin, East African features, tightly curled hair / cornrow braids (shuruba)". Seeds 4101–4103 unchanged.
- **Result:** in the first reference sheet, the father and both daughters read as Mediterranean or Latin American. After the change, all three read as Habesha, and every keyframe conditioned on them followed. Five of five character shots now show the same family.
- **Evidence:** `runs.jsonl`, the `ref:father`, `ref:daughter_child` and `ref:daughter_adult` lines at 16:51Z and 16:53Z (two prompts, same seed); git diff of `storyboard.json` in commit "Storyboard contract v2…" and later.
- **Lesson:** describing the qualities (skin, hair, features, clothing) works. The word "Ethiopian" by itself did not.

## E2. Conditioning the adult daughter on the child's reference
- **Hypothesis:** generating the 25-year-old daughter with the child's portrait as `input_image_0` ("the girl from image 1, grown up") will make the two read as one person.
- **Change:** `derived_from: daughter_child` on `daughter_adult`.
- **Result:** first attempt: the "adult" came back as a child; the reference image dominated the age in the text. Second attempt, with "grown adult, mature proportions" in the prompt: the provider's output filter refused it (`ref:daughter_adult`, error, 16:53:52Z). Dropped `derived_from`. The adult now shares the child's written description (round face, big dark eyes, tibeb border) and her own reference seed.
- **Evidence:** `runs.jsonl` `ref:daughter_adult` error line; `storyboard.json` consent note on `daughter_adult`.
- **Lesson:** image conditioning transfers age as strongly as identity. Continuity across an age jump has to come from shared wording and wardrobe, not from the child's face.

## E3. Spatial blocking in the prompt fixes "who is in the basin"
- **Hypothesis:** "the girl washing her father's feet" is ambiguous to the model, which has to guess whose feet go in the basin.
- **Change:** shots 1 and 2 were rewritten to say where each body is. Shot 2 became "the father sits on a low wooden chair with his feet in a metal basin; the girl kneels on the mat beside the basin". Seed unchanged (102).
- **Result:** before, the girl was standing in the basin (shot 1) or sitting in it (shot 2). After, the father's feet are in the basin and the girl kneels beside it with his hand on her head: the film's motif.
- **Evidence:** `shot_02.v` lines in `runs.jsonl` with the two prompts; `outputs/keyframes/shot_02.v.png.meta.json` holds the final prompt.

## E4. Showing the ritual as an insert shot instead of the child's face
- **Hypothesis:** the filter reacts to the combination of child, bare feet and adult man. An insert shot of hands, water and the basin tells the same beat without that combination.
- **Change:** shot 1 changed from `medium_close_up` with `daughter_child` to `insert_shot` with no character. The prompt describes small hands, the clay pitcher and the dress hem with its tibeb border, so the child is still identifiable by wardrobe.
- **Result:** shot_01.v passed at the first try. The film now opens on the act before the faces, which also makes a better first image: the audience learns what the ritual is before who does it.
- **Evidence:** `runs.jsonl`, `shot_01.v` error at 16:54:18Z, then ok at 16:54:39Z with the insert-shot prompt.

## E5. Is the output filter deterministic?
- **Hypothesis:** a flagged prompt and seed will be flagged every time, so reseeding is the only fix.
- **Change:** none to the prompt. Re-ran `shot_01.h` with the same prompt, same seed (101) and same inputs.
- **Result:** **hypothesis wrong.** `shot_01.h` was flagged at 16:54:45Z and passed with the identical request at 16:55:08Z. The filter is not deterministic. `keyframes._make` now retries a flagged output with derived seeds (`seed+1000`, `seed+2000`) and records `seed_used`. `shot_03.h` needed it (seed 103 flagged, 1103 passed), and so did E6 below.
- **Evidence:** `runs.jsonl` `shot_01.h` error and ok lines; `outputs/keyframes/shot_03.h.png.meta.json` has `"seed_used": 1103`.

## E6. Conditioning the 16:9 keyframe on its 9:16 sibling
- **Hypothesis:** the character reference alone keeps the *person* consistent between aspect ratios, but not the *set and light*. Adding the 9:16 keyframe as a second reference will make the two versions show the same moment.
- **Change:** generated shot 5's 16:9 frame once more with only the character reference (no sibling), same prompt minus the "same scene" lead, same seed family.
- **Result:** both 16:9 versions have the same woman, so identity comes from the reference sheet. Without the sibling, the courtyard changed: stone paving instead of earth, a palm tree, a cooler blue sky, a different house. With the sibling (the pipeline's default), it is the same courtyard, ground and warm light as the vertical cut. Kept sibling conditioning. It costs nothing extra, because the 16:9 call was needed anyway.
- **Evidence:** `outputs/experiments/E6_shot_05.h.no_sibling.png` vs `outputs/keyframes/shot_05.h.png`; `runs.jsonl` `E6:shot_05.h-no-sibling` (the first seed was flagged too, again E5).

## E7. Choosing the score among three seeds with a measurable criterion
- **Hypothesis:** under narration, the candidate with the least energy in the speech band (300–3400 Hz) will compete least with the voice.
- **Change:** three candidates (seeds 11, 23, 42), same caption, bpm and cues. Measured `voice_band_share` for each.
- **Result:** 0.0953 / **0.0923** / 0.0943 → seed 23. The spread is small (3%), because the composer's register is fixed by the mode, so the number is a tie-breaker. The deciding test is the listen under narration in the second user test (DESIGN.md).
- **Evidence:** `outputs/music/candidates.json`; `storyboard.json` `music.selection_reason`.

## E8. The brief's ducking settings vs my "gentler" guess
- **Hypothesis (mine):** the suggested 0.02 / 6 / 300 ms / 1500 ms is too aggressive for a quiet score and will make it vanish. My own 0.05 / 4 / 120 / 900 would sound more natural.
- **Change:** `make duck-sweep` ducks the real music stem by the real narration stem under four settings and measures the music alone under speech and in the pauses.
- **Result:**

| Setting | threshold / ratio / attack / release | Music under speech | Duck depth | Music lost in pauses |
|---|---|---|---|---|
| none | — | −25.0 dBFS | 0.0 dB | 0.0 dB |
| brief default | 0.02 / 6 / 300 ms / 1500 ms | −36.5 dBFS | **11.5 dB** | 0.4 dB |
| my guess ("gentle") | 0.05 / 4 / 120 ms / 900 ms | −29.8 dBFS | 4.8 dB | 0.0 dB |
| soft | 0.1 / 3 / 100 ms / 700 ms | −27.0 dBFS | 2.0 dB | 0.0 dB |

  The suggested setting ducks more than twice as deep and gives back almost everything in the pauses (0.4 dB). My guess barely ducked. Adopted the brief's setting, and raised the music bed from −9 dB to −6 dB so the pauses are fuller.
- **Evidence:** `outputs/experiments/duck_sweep.json`; `pipeline/tools/duck_sweep.py`; commit "Storyboard: adopt the measured ducking setting…".

## E9. True peak after AAC encoding
- **Hypothesis:** a master normalised to −1 dBTP stays under −1 dBTP after AAC encoding.
- **Change:** none, measured. Then set the master's ceiling 0.7 dB lower (`CODEC_HEADROOM_DB`).
- **Result:** first export: −14.4 LUFS but **−0.8 dBTP**. The encoder created inter-sample peaks above the ceiling. With the 0.7 dB of headroom: −14.4 LUFS and −1.5 dBTP in both files.
- **Evidence:** `outputs/final/qc.json` (current); the first value is in the commit message of "Assemble: two-line subtitles in 9:16 and codec headroom for true peak".

## E10. Subtitle size for the vertical frame
- **Hypothesis:** the same subtitle style works in both aspect ratios.
- **Change:** looked at frames from both exports; then wrote `test_subtitles_never_exceed_two_lines`.
- **Result:** at size 58 the 9:16 subtitles wrapped to three lines ("In every success of / mine, I remember my / father's pure heart."). Moved to size 46 with 34 characters per line. The test then caught a second case: a 68-character chunk can still wrap to three lines at 34. Such chunks are now split into consecutive two-line events.
- **Evidence:** `tests/test_stages.py`; commits "Assemble: two-line subtitles…" and "Fix: a subtitle chunk could still wrap to three lines in 9:16".

## E11. Let the measured narration set the cut
- **Hypothesis:** the planned shot lengths (9–10 s, 75 s in total) will fit the Amharic narration.
- **Change:** `timeline.build` takes `max(planned, 0.7 + speech + 1.1)`.
- **Result:** three shots were too short for their line. Shot 2, the father's blessing and the longest line, has 9.7 s of speech in a 9 s shot. Shots 4 and 5 were stretched as well. The film is 81.25 s instead of 75, still inside 60–90, and no line is cut off.
- **Evidence:** `outputs/timeline.json` (`stretched: true`).

## E12. Does a one-line storyboard edit really regenerate only that shot?
- **Hypothesis:** with content-hash caching, editing shot 8's keyframe prompt causes 2 image calls and nothing else.
- **Change:** shot 8's 16:9 frame had drifted indoors while the 9:16 was outdoors. Rewrote its prompt to "standing outdoors on a highland hilltop at golden hour…" and ran `make film`.
- **Result:** run `20261126T202007-6196`: **2 model calls** (shot_08.v, shot_08.h), 2 clips re-rendered, mix and exports rebuilt. 17 images, 8 narration lines and 14 clips cached. Both versions of shot 8 are now outdoors in the same light.
- **Evidence:** `runs.jsonl` lines with that `run_id`.

## E13. Ceiling: the father's blessing in Tigrinya and Afaan Oromo
- **Hypothesis:** the same pipeline can narrate the film in Tigrinya and Afaan Oromo by adding a translation step: Gemini text → the same TTS voice and style. Tigrinya, which is on the TTS language list, will work. Afaan Oromo, which is not on the list, will fail or come out garbled.
- **Change:** `python -m pipeline.tools.lang_test` translates shot 2's Amharic line, voices it with `gemini-3.8-flash-lite-tts` "Kore", and measures it against the Amharic take (9.70 s). One TTS call per language, because of the quota.
- **Result:**

| | Tigrinya | Afaan Oromo |
|---|---|---|
| Translated by | gemini-3.1-flash-lite, after 3.8 Flash and 3.5 Flash returned 503 (F10) | same |
| TTS | audio returned, −19.9 dBFS RMS | **audio returned too**, −18.1 dBFS RMS, although Oromo is not on the TTS language list |
| Speech length | 10.12 s, **1.04×** the Amharic: fits the existing 11.5 s shot | 13.95 s, **1.44×**: shot 2 would stretch to ~15.8 s and the film to ~85.5 s, still under 90 |
| Text | «እግዚአብሔር ይባርክሽ፤ በመንገድሽ እግዚአብሔር ይቅደምልሽ፣ በጥበብን ብልሃትን የዓድለሽ» ይለኒ ነበረ። | "Waaqayyo si haa eebbisu; karaa kee hundumaa irratti Waaqayyo si dura haa deemu; hubannaa fi ogeessummaan si haa guddisu" jedhee natti hime ture. |

  **The hypothesis was half wrong.** TTS did not refuse Oromo. The real weak spot looks like the *translation*. The Tigrinya line keeps Amharic verb forms (ይባርክሽ, ይቅደምልሽ are Amharic; the ending ይለኒ ነበረ is Tigrinya), so it looks like Amharic leaking into a lighter model's Tigrinya. That is a suspicion, not a verdict: neither author is a native Tigrinya or Oromo speaker.
- **Native-speaker check (pending):** a Tigrinya speaker and an Oromo speaker listen to `outputs/experiments/lang/shot_02.{ti,om}.wav` and answer: (1) Is the text your language, or mixed with Amharic? (2) Is the pronunciation understandable? Where does it break: names, ejectives, long vowels? (3) Would you watch the film in this voice? Record the answers here.
- **What it shows about the pipeline:** a second language is one new storyboard field per shot plus this translation step. The timeline already absorbs the 1.44× length difference, so the Oromo cut would still be inside 60–90 s.
- **Evidence:** `outputs/experiments/lang/results.json`, the two WAVs, and the `E13:*` lines in `runs.jsonl`.
