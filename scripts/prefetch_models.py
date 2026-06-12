"""One-command programmatic model prefetch (BUILD.md §5).

BFL repos (FLUX.2-klein-4B, the default image model) are usually access-walled even
when Apache-2.0: click "Agree to access" once on the HF page and set HF_TOKEN in .env.
The token is passed when present, so this works for both gated and ungated repos.

Run once: uv run python scripts/prefetch_models.py
"""

import os

from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

REPOS = [
    "black-forest-labs/FLUX.2-klein-4B",  # default image model (Apache-2.0; may require a one-time HF gate click)
    "Lightricks/LTX-Video",
    "hexgrad/Kokoro-82M",
    "ACE-Step/ACE-Step-v1-3.5B",
    # Optional upgrades (need HF_TOKEN + a one-time license click):
    # "black-forest-labs/FLUX.1-Kontext-dev",
    # "stabilityai/stable-audio-open-1.0",
]

token = os.environ.get("HF_TOKEN") or None
for repo in REPOS:
    print("↓", repo)
    snapshot_download(repo_id=repo, token=token)  # → ~/.cache/huggingface
print("All models cached.")
