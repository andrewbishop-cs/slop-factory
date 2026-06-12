"""One-command programmatic model prefetch (BUILD.md §5).

`FLUX.1-schnell` is gated on Hugging Face (Apache-2.0 license, but access-walled):
click "Agree to access" once on its HF page and set HF_TOKEN in .env. The other
default-stack models are ungated. Optional upgrades stay commented out.

Run once: uv run python scripts/prefetch_models.py
"""

import os

from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

UNGATED = [
    "Lightricks/LTX-Video",
    "hexgrad/Kokoro-82M",
    "ACE-Step/ACE-Step-v1-3.5B",
]
GATED = [  # needs HF_TOKEN + a one-time license click on each repo's HF page
    "black-forest-labs/FLUX.1-schnell",
    # "black-forest-labs/FLUX.1-Kontext-dev",
    # "stabilityai/stable-audio-open-1.0",
]

for repo in UNGATED:
    print("↓", repo)
    snapshot_download(repo_id=repo)  # → ~/.cache/huggingface
for repo in GATED:
    print("↓", repo)
    snapshot_download(repo_id=repo, token=os.environ["HF_TOKEN"])
print("All models cached.")
