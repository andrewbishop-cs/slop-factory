"""M0 checkpoint test (BUILD.md §10):
1. torch MPS available
2. the §8 example episode validates against schemas.Episode (and malformed input is rejected)
3. settings.yaml + series bible load cleanly
"""

import torch
from pydantic import ValidationError

from src.config import load_series_bible, load_settings
from src.schemas import Episode

EXAMPLE_EPISODE = """
{
  "episode_id": "sewer-surfers_ep_0007",
  "series_id": "sewer-surfers",
  "title": "The Spillway Showdown",
  "hook_text": "He hit the spillway at full speed.",
  "hook": {
    "type": "video",
    "prompt": "surfer on a neon hydro-board rockets off a sewer spillway, huge spray, exaggerated wipeout, dynamic camera, polished Pixar-style 3D cartoon-realism",
    "library_clip": null,
    "duration_sec": 3.5,
    "sfx": "rushing water then a comedic splash"
  },
  "characters_present": ["circuit", "riptide"],
  "scenes": [
    {
      "id": 1,
      "image_prompt": "<circuit appearance_tokens> crouched on a glowing hydro-board in a dim flood tunnel, neon light on wet concrete, <style_anchor>",
      "motion": { "type": "ken_burns", "move": "push_in", "duration_sec": 6 },
      "narration_text": "Circuit had run the numbers a thousand times. Tonight, the math would finally beat the madman.",
      "top_text": null,
      "mood": "tense-calm",
      "intensity": 0.3,
      "duration_sec": 6
    }
  ],
  "cliffhanger_text": "Who takes the next heat? Crown's still up for grabs.",
  "music": { "global_mood": "high-energy underground race tension", "bpm_hint": 128 },
  "caption": {
    "description": "Gadgets vs. guts in the sewer race for the crown 🌊 #aianimation #cartoon #brainrot",
    "hashtags": ["#aianimation", "#cartoon", "#sewersurfers"],
    "ai_label": true
  },
  "target_duration_sec": 72
}
"""


def main() -> None:
    mps = torch.backends.mps.is_available()
    print(f"MPS available: {mps}")
    assert mps, "MPS not available"

    ep = Episode.model_validate_json(EXAMPLE_EPISODE)
    print(f"Example episode validates: {ep.episode_id} — '{ep.title}', total {ep.total_duration_sec}s")

    try:
        Episode.model_validate_json('{"episode_id": "ep_bad", "scenes": []}')
        raise AssertionError("malformed episode was accepted")
    except ValidationError:
        print("Malformed episode correctly rejected")

    settings = load_settings()
    print(f"Settings load: image={settings.image.backend}/{settings.image.model}, video={settings.video.width}x{settings.video.height}@{settings.video.fps}")

    bible = load_series_bible("sewer-surfers")
    print(f"Series bible loads: {bible.series_id} — {len(bible.characters)} characters")

    print("\nM0 checkpoint: ALL PASS")


main()
