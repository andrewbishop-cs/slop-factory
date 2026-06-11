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
  "episode_id": "ep_0007",
  "series_id": "fridge-detectives",
  "title": "The Banana Peel Betrayal",
  "hook_text": "He never saw it coming.",
  "hook": {
    "type": "video",
    "prompt": "cartoon walnut detective in a fedora slips on a banana peel, exaggerated slapstick fall, dynamic camera, 3D Pixar style",
    "library_clip": null,
    "duration_sec": 3.5,
    "sfx": "comedic whoosh then thud"
  },
  "characters_present": ["walnut", "banana"],
  "scenes": [
    {
      "id": 1,
      "image_prompt": "<walnut appearance_tokens> sitting in a dim fridge office, neon light, <style_anchor>",
      "motion": { "type": "ken_burns", "move": "push_in", "duration_sec": 6 },
      "narration_text": "Detective Walnut thought it was an ordinary Tuesday.",
      "top_text": null,
      "mood": "noir-calm",
      "intensity": 0.3,
      "duration_sec": 6
    }
  ],
  "cliffhanger_text": "Who left the peel? Part 8 tomorrow.",
  "music": { "global_mood": "noir comedic tension", "bpm_hint": 90 },
  "caption": {
    "description": "Detective Walnut's worst Tuesday yet 🥜 #aianimation #cartoon #brainrot",
    "hashtags": ["#aianimation", "#cartoon", "#fridgedetectives"],
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

    bible = load_series_bible("fridge-detectives")
    print(f"Series bible loads: {bible.series_id} — {len(bible.characters)} characters")

    print("\nM0 checkpoint: ALL PASS")


main()
