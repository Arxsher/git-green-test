# Production stack: making this format with your tools

How to produce a low-poly 3D, dialogue-driven mini sitcom like @canwebuildthis with **Google AI Pro** and **ChatGPT Pro**, plus a cheap voice tool.

Facts about the tools come from web research on 13 Oct 2026. Most of it is from search summaries, not the vendors' own pages, and plans and credit prices change often. Check the numbers inside each app before relying on them.

---

## First: what the original needs (and what it doesn't)

From the teardown (`01-account-teardown.md`), the format needs only:

| Need | Why it matters for production |
|---|---|
| One fixed set, three camera angles: close-up of her, over-the-shoulder on the AI, and a wide two-shot | Only about 3–5 "plates" per lighting mood, reused across episodes |
| Characters that never change | Consistency is the hard part with AI video |
| Crude mouth movement | Her mouth only swaps between 3–4 flat shapes. **The AI characters have no mouths at all.** Exact lip sync is **not** needed |
| Separate voices per character | The voice does the acting, not the animation |
| One caption per line | Edited in, not generated |
| No music | Dialogue plus a faint room tone only |

So you don't need a model that can act. You need **consistent stills, short "talking" and "listening" loops, good voices, and tight editing.** That is very achievable with your plans.

---

## Your tools, as of Oct 2026

### "Veo Omni" is really Gemini Omni (Google AI Pro)

There is no product called "Veo Omni." Google's current video model is **Gemini Omni**, announced at Google I/O in May 2026; version **Omni 1.1 Flash** came out on 27 Aug 2026. It replaced Veo in the Gemini app. Veo 3.1 is still available in **Flow**, Google's filmmaking app.

- Google's announcement: https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni/
- Omni 1.1: https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-omni-1-1-flash/
- Gemini video overview: https://gemini.google/overview/video-generation/

**Use Flow, not the Gemini app**, because Flow has the controls this format needs:

| Flow feature | What you use it for |
|---|---|
| **Frames to Video** (first frame, or first and last) | Start every clip from your approved still, so the character and set never drift |
| **Characters** (`@Name`) | Save each character with reference images and a voice reference, then call it by name in prompts. Help: https://support.google.com/flow/answer/16353334 |
| **Extend** | Omni 1.1 extends in 10 s steps, up to about 40 s total |
| 360p draft, then free upscale | Draft cheaply, then upscale only the keepers to 720p/1080p |

**Credits (Google AI Pro: 1,000 Flow credits a month, no rollover).** Help: https://support.google.com/flow/answer/16526234

| Generation | Credits |
|---|---|
| Omni 360p draft, 10 s | 7 |
| Omni 720p, 10 s | 15 |
| Veo 3.1 Lite / Fast / Quality | 10 / 20 / 100 |
| Upscale to 720p or 1080p | free |

That is about **140 ten-second drafts a month**, which is plenty if you build reusable loops (see the workflow below) instead of generating every line fresh.

**Watermark.** A visible watermark is on by default. Turn it off in Gemini → Settings → Media Watermark; Flow got the same toggle in Aug 2026. The invisible SynthID mark always stays. Help: https://support.google.com/gemini/answer/17405358

**Known weak spots** (reported, not tested here):
- A 9:16 input has sometimes come back as 16:9. Always check the output's aspect ratio.
- Consistency drops when the camera moves a lot. Keep camera moves tiny, as the original does.

**Music.** Flow Music (Lyria) is included with commercial rights. The original uses no music, though.

### ChatGPT Pro: images only now

- **Use ChatGPT Images 2.5** (released 8 Sep 2026). It keeps a reference subject consistent better than earlier versions and handles multi-turn edits well. https://openai.com/index/introducing-chatgpt-images-2-5/
- **Sora is gone.** OpenAI shut the Sora app on 26 Apr 2026 and the API on 24 Sep 2026, so ChatGPT Pro no longer makes video. https://help.openai.com/en/articles/20001152-what-to-know-about-the-sora-discontinuation
- **What it's for here:**
  - the character sheets
  - the set
  - the lighting variants
  - every first frame you feed into Flow

### Voices: add ElevenLabs (about $6–22/month)

The voices carry this format, so lock them in a dedicated voice tool rather than leaving them to the video model.

- **Voice Design** creates a voice from a text description. https://elevenlabs.io/voice-design
- **Voice Changer** lets you act out a line yourself and convert it into the character's voice. This is the best way to get the comic timing right. https://elevenlabs.io/voice-changer
- **Plans:**
  - Starter ($6) includes a commercial licence.
  - Creator ($22) adds professional voice cloning.
  - Pricing: https://elevenlabs.io/pricing

The alternative is Flow's native voice with a voice reference on each Character. It's convenient, but you have less control over the delivery.

### Editing: CapCut or Instagram's Edits app

- **Edits** (free, from Meta) posts straight to Instagram and has auto captions.
- **CapCut** gives finer caption styling.
- **Music licences:**
  - CapCut's "commercial sounds" are licensed only for CapCut and TikTok, not Instagram. You don't need them anyway.
  - Instagram's music library is for personal accounts. Business accounts are limited to the Meta Sound Collection.

---

## Route A: the AI route, using what you already pay for

### Step 1: design the cast and set (ChatGPT Images 2.5)

- **Design your own characters and set** in the same family of style (see `03-replication-playbook.md` for why not to copy theirs).
- **Style words that describe the original look:**
  - low-poly 3D
  - flat-shaded facets
  - soft studio lighting
  - shallow depth of field
  - chunky simple shapes
  - mitten hands
  - dot eyes
  - a flat rectangular mouth
  - "toy-like," like a Blender render
- **For each character, generate:**
  - a front / three-quarter / side turnaround
  - 4 expressions: neutral, flat stare, surprised, small smile
  - 4 mouth shapes for the human: closed line, small open, wide open, "o"
- **For the set, generate:**
  - one wide shot of the room
  - a close-up framing of the human
  - an over-the-shoulder framing of the AI character, with her shoulder blurred in the foreground
- **Then restyle that same set into 4–5 lighting moods.** Changing only the light keeps the feed varied while the set stays recognisable:
  - night (navy with a warm key light)
  - dusk (purple-pink)
  - golden hour
  - rainy daylight
  - morning
- **Keep a written "bible":** one fixed paragraph per character and per set, pasted word for word into every prompt.

### Step 2: build reusable motion loops (Flow, Omni 1.1)

Instead of generating each line of dialogue, build a **library of loops per camera angle and lighting mood**:

| Clip | Count per mood | Notes |
|---|---|---|
| Human close-up, talking | 2–3 × 10 s | Small head movement, mouth moving, no camera move. Prompt says "no on-screen text, no music" |
| Human close-up, listening / deadpan | 2 × 10 s | Blink, tiny sway |
| AI over-the-shoulder, "talking" bounce | 2 × 10 s | A gentle squash-and-bounce reads as speech for a mouthless mascot |
| AI over-the-shoulder, idle | 1 × 10 s | |
| Wide two-shot | 2 × 10 s | One neutral, one with a small gesture |

That's about 10 clips per mood: roughly 70 credits at 360p, then free upscales. **Five moods cost about 350 credits once, and you reuse them across dozens of episodes.**

- **Spend the rest of the month's credits on special shots:** her holding a phone, lying on a couch, a new prop.
- **Prompt skeleton** (Google's documented order is cinematography, subject, action, context, style):

> Vertical 9:16, static close-up, very slow push-in. @Mira sits at her desk at night, looking at camera-left, talking calmly. Low-poly 3D toy style, flat-shaded facets, warm key light from the monitor, cool navy window with blurred city lights behind, shallow depth of field. Ambient noise: quiet room tone. No music, no on-screen text, no camera shake.

- **Check every clip against the character sheet:** look at the first, middle and last frames, and only keep clips that match.

### Step 3: record voices (ElevenLabs)

- Generate each line on its own, using one locked voice per character.
- Export everything to one folder, numbered in script order.

### Step 4: assemble (CapCut or Edits)

- Lay down the voice lines with **0.2–0.6 s gaps**. The original's gaps are in that range, with a longer ~0.9 s pause before a punchline.
- **Cut to whoever is speaking on every line.** Trim a talking loop to the line's length.
- Use the wide shot about 2–3 times: early, once in the middle, and **always for the final line** (the button).
- **Add one caption per line:**
  - white bold sans-serif
  - a dark semi-transparent rounded box
  - in the upper third
  - appearing on the first word
- Add a faint room-tone bed about 28 dB under the voices (rain for rainy episodes, city hum at night).
- Export 1080×1920, at a loudness around -14 to -16 LUFS, which matches the original.

---

## Route B: the real 3D route (closest to the original)

The original looks like a real 3D render, most likely Blender. The same models, props and screen graphic appear from every angle across six episodes, with none of AI video's drift. Building it this way costs more effort once and very little per episode afterwards.

- **Claude can drive Blender directly.**
  - Anthropic's Blender connector launched in April 2026, and Blender Lab ships an official MCP server: https://www.blender.org/lab/mcp-server/
  - It can build the low-poly set and simple characters, place the 3 cameras, set up the lighting moods, and render.
- **Weak spots:** organic character modelling and rigging still need hand fixes, and long sessions use a lot of tokens.
- **Once the scene exists, an episode is:**
  1. script
  2. voices
  3. mouth shapes swapped automatically from the audio
  4. one camera cut per line
  5. render
  6. captions
- You would need a computer with Blender. Claude would do the scripting; you wouldn't write code.

**Recommendation:** start with Route A to test whether your version of the format catches on, ideally with 5–10 episodes. If it does, move to Route B for perfect consistency and near-zero cost per episode.

---

## Monthly cost

| Item | Cost |
|---|---|
| Google AI Pro (Flow credits, Omni) | already paid |
| ChatGPT Pro (Images 2.5) | already paid |
| ElevenLabs Starter or Creator | $6–22 |
| CapCut Pro (optional; Edits is free) | $0–20 |
