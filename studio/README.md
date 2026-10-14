# Studio: our 3D episode pipeline

How an episode gets made, all on a cloud machine with no GPU:

1. **`build_scene.py`** (Blender) builds the set: her desk with the window on her right, the city at dusk, her, and Claude. It also places three cameras: close-up, over-the-shoulder and wide.
2. **`episodes/*.json`** holds the script, one line at a time: who speaks, which camera, and the text.
3. **`voices.py`** voices every line with a free open-source voice model (Kokoro) and lays out the timing.
4. **`render_plates.py`** (Blender) renders each camera once per pose: mouth shapes, blinks, and Claude's bounce.
5. **`compose.py`** builds every frame from those plates in sync with the voices, then adds slow push-ins, captions and room tone, and exports the MP4.

Only mouths, blinks and the bounce move ("limited animation"), so one episode needs about 20 renders instead of 1,500.
