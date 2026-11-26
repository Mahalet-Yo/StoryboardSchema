# Design: The Blessings of Pure Hands

## 1. Brief

| | |
|---|---|
| **Logline** | A daughter who once washed her father's feet carries his spoken blessing through his death and into her adult life. |
| **Format** | 81 s heritage short, 9:16 (phone feeds) and 16:9 (YouTube), Amharic narration, English subtitles, original score, AI end card |
| **Who watches** | Ethiopians at home and in the diaspora who grew up with parental blessings (*mirkat*); young adults who value family heritage; anyone who has lost a parent |
| **Where** | On a phone, mostly vertical, often shared in family Telegram/WhatsApp groups. Sound may be off, so the subtitles must carry the story alone |
| **Intent** | At the end, the viewer should feel that a parent's blessing doesn't end with the parent, and want to call or remember their own father or mother |
| **Define** | How might we help young Ethiopians feel the weight of a parent's *mirkat* in 80 seconds, without a funeral scene or a sermon? |

## 2. Creative vision

The film is about the relationship between an Ethiopian father and his daughter, and about how values pass between generations through a parent's blessing. It should feel emotional, peaceful, respectful and culturally specific rather than generic.

**Structure (three beats):**
- **Beginning, the ritual:** a young daughter washes her father's feet and he blesses her. This sets up the custom and the bond.
- **Middle, the loss:** years pass and the father dies. Shown as an empty landscape at dawn, never as a funeral.
- **End, the fulfilment:** the grown daughter lives the life he wished for her, and he rejoices from heaven.

**Motifs:**
- the father's hand on her head (shot 2), echoed by the light on her face (shots 5–6);
- warm water and morning light: purity, then renewal.

**Look:** warm 35 mm film still, soft window light, earth tones with amber highlights, Ethiopian highland home, white cotton with a green-yellow-red tibeb border on the daughter at both ages, the visual thread that says "same person". The style block in `storyboard.json` is attached to every prompt.

**Sound:**
- Amharic narration in a warm, unhurried, close voice, as a grown daughter remembering.
- Under it, a sparse krar-like score in the tezeta mode, the mode of Ethiopian nostalgia songs. It opens up at the time jump, is fullest at the fulfilment, and resolves on the tonic under the end card.

## 3. Shot list: every shot has a reason

| Shot | Size / move | Reason (also in `storyboard.json`) | Narration (English subtitle) |
|---|---|---|---|
| 1 | medium close-up (profile), push in | Opens on the daughter's face as she pours: the audience meets her before the ritual. Was an insert of hands and water until test 2 asked for her face (§6) | As a child, washing my father's feet, my heart would fill with so many blessings. |
| 2 | medium, pull out | Father and daughter in one frame; the hand on the head is the film's motif | 'May God bless you, may He go before you on your path, may He raise you in wisdom and understanding,' he would say. |
| 3 | close-up, push in | The child's face is where the words land: the seed the rest of the film grows from | Words from a pure heart were sown in me like a seed, and they grew. |
| 4 | wide establishing, pan right | An empty landscape and an empty chair carry the time jump and the death without a funeral | Many years passed. My father went home to his Creator, but his blessing stayed with me. |
| 5 | medium, push in | The blessing fulfilled: the same girl, grown, standing in the light he wished for her | The peace, wisdom and honour he wished for me came true in my life, one by one. |
| 6 | close-up, tilt up | The emotional peak: gratitude, mirroring the child's close-up in shot 3 | In every success of mine, I remember my father's pure heart. |
| 7 | extreme wide, tilt down | Moves to the father's point of view; a luminous sky instead of a literal heaven keeps it reverent for any faith | And when my father looks on my life from heaven, his heart fills with joy. |
| 8 | medium close-up, pull out | Closes the circle on the father's face: the joy of the one who gave the blessing | Seeing his daughter live by his blessing, he rejoices. |
| end card | 3.5 s | Honest labelling: Made with AI, sources, fictional characters | — |

## 4. User test 1: the radio cut (narration + placeholder music, black screen)

**When / who:** before the narration revision of 25 November 2026 (commit `2afb02c`). Three people from the intended audience heard the radio cut and said what they felt and what they would change. The notes below are what was recorded at the time.

| Feedback area | What they said |
|---|---|
| Story and message | All three liked the story. |
| Cultural connection | All three said they could relate to it personally: the father–daughter bond and the meaning of a parent's blessing. |
| Emotional impact | The words were not yet strong enough. They asked for more emotionally expressive wording. |
| Suggested improvement | Revise some narration lines so the emotion comes through more strongly and naturally. |

**What changed because of it** (commit `2afb02c`, "Update narration text in storyboard.json", 25 Nov):

| Shot | Before the test | After the test | Intent of the edit (our reading) |
|---|---|---|---|
| 1 | …ልቡ በንጹህ ምርቃት ይሞላ ነበር ("*his* heart would fill with pure blessings") | …**ልቤ በብዙ** ምርቃት ይሞላ ነበር ("*my* heart would fill with so many blessings") | The blessing is felt by the daughter; first person makes it hers |
| 2 | መንገድሽ የተከፈተ፣ ልብሽም የተረጋጋ ይሁን ("may your path be open and your heart at peace") | **በመንገድሽ እግዜብሄር ይቅደምልሽ፣ በጥበብ እና በማስተዋል ያሳድግሽ** ("may God go before you on your path, may He raise you in wisdom and understanding") | Closer to the words a father actually says, rather than a paraphrase |
| 3 | በንጹህ ልብ የወጣ ቃል … ተተክሎ አደገ ("a word… was planted") | ከንጹህ ልብ የወጡ **ቃላቶች** … **ተዘርተው** አደገ ("words… were sown") | Sowing a seed is the stronger image, and it sets up the harvest in shot 5 |
| 7 | ልቡ በደስታ **ተሞላ** (past: "was filled") | ልቡ በደስታ **ይሞላል** (present: "fills") | The father is still watching: the blessing is alive, not finished |
| 8 | …እግዚአብሔርን ከልብ አመሰገነ ("he thanked God from his heart") | …**ይደሰታል** ("he rejoices") | Ends on the father's joy, which is the feeling the film should leave |

The English subtitles were then rewritten to match the revised Amharic. The earlier versions had drifted ("my heart would fill with pure alot of blessings", "his heart will fill with joy").

## 5. What production taught us (changes to the storyboard after test 1)

These were not audience feedback; they came from looking at the generated material. Details and evidence are in EXPERIMENTS.md.
- **Characters looked Mediterranean, not Ethiopian.** The descriptions now name skin tone, features, hair and the tibeb border (E1). This mattered most for this audience: the people in the film have to look like their own families.
- **The child is never conditioned on an adult's image, and vice versa** (E2). Continuity across the 17-year jump comes from the shared description and the tibeb border, which appears at both ages.
- **Shot 1 became an insert of hands and water** (E4), to get past the output filter. Test 2 rejected it: viewers wanted her face first, so §6 changes it again.
- **The measured narration set the cut** (E11). Shot 2, the blessing, got the 11.5 s it needs, so the most important line is never rushed.
- **Ducking from the brief beat my guess** (E8): the voice stays clear without the music vanishing.

## 6. User test 2: the near-final cut

**When / who:** 26 November 2026. Three people from the intended audience watched the near-final vertical cut (81.25 s, the version committed before this change) and answered the seven questions below. Their answers were compiled into one set; where they agreed, the answer below is the shared one.

| # | Question | What they said | Reading |
|---|---|---|---|
| 1 | In one sentence, what is the film about? | "The relationship, love and respect between an Ethiopian father and daughter." | ✓ The story lands without explanation; matches the logline |
| 2 | What did you feel at the end? | "I feel the emotion the girl feels." | ✓ Close to the intent (the blessing lives on in her); they identify with the daughter |
| 3 | Did the girl and the woman read as one person; the father the same in shots 2 and 8? | Yes | ✓ The reference-sheet approach works (E1, E2, E6) |
| 4 | Was any Amharic word mispronounced or unnatural? Which shot? | **Yes: shot 3 and "9"** | ✗ Narration problem (see below) |
| 5 | With sound off, could you follow from the subtitles alone? | Yes | ✓ Subtitles carry the story |
| 6 | Was the music ever too loud under the voice? | No | ✓ Confirms the ducking choice from E8 by ear |
| 7 | Hands first (shot 1), or her face first? | **"I would rather see her face."** | ✗ Change shot 1 |

A separate viewer comment from the same round: the narrator "doesn't sound fluent" in places, especially the father's blessing (shot 2).

### What changed because of it

| Feedback | Change | Status |
|---|---|---|
| Q7: see her face first | Shot 1 changed from an insert of hands and water to a profile medium close-up of the girl's face as she pours from the clay pitcher. The father's feet stay out of frame, which keeps it clear of the output filter (F3). Reason updated in `storyboard.json`. First try merged the oil lamp and the pitcher (she "poured" from a lit lamp); the second prompt names a clay pitcher and puts the light off frame (EXPERIMENTS E14) | **Done.** 4 image calls, only shot 1 regenerated |
| Q4: shot 3 sounds wrong | Likely cause in the text: ከንጹህ ልብ የወጡ **ቃላቶች** … ተዘርተው **አደገ** has a plural subject with a singular verb, and ቃላቶች is a double plural. The proposed line is ከንጹህ ልብ የወጡ **ቃላት** … ተዘርተው **አደጉ**, to be confirmed by a native speaker | **Blocked:** re-voicing needs TTS, and both TTS models are out of daily quota until after the deadline (FAILURES F11) |
| Q4 "9" and the fluency comment: shot 2 | Shot 2 starts at 9 s, so "9" most likely points at the father's blessing. That line spelled God two ways (እግዚአብሔር / እግዜብሄር) and used curly quotes; the fix is one spelling and «…». The deeper cause is the smaller Flash-Lite TTS model (F2, F11) | **Blocked** for the same reason; the text fix is written and ready |

**What we learned:** the pictures and the mix now work for this audience. The weak link is the Amharic voice, and that is a quota problem, not a design one: the full Flash TTS model and two corrected lines are the first thing to redo when the quota resets.

## 7. Reflection

What mattered most was keeping the story's emotional and cultural meaning, not image quality alone. Every generated element went through human judgement: the narration through native-speaker testers, the faces through a check that they look like the people this film is for, and the music through a measurement and a listen under the voice. The intended feeling is simple: a parent's love, wisdom and blessing stay with a child across generations.
