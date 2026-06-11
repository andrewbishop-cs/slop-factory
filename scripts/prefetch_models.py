"""One-command programmatic model prefetch (BUILD.md §5).

All default-stack models are ungated — no HF token needed. Gated optional
upgrades are commented out; enable them only after clicking "Agree" on the
repo's HF page and setting HF_TOKEN in .env.

Run once: uv run python scripts/prefetch_models.py
"""

import os

from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

UNGATED = [
    "black-forest-labs/FLUX.1-schnell",
    "Lightricks/LTX-Video",
    "hexgrad/Kokoro-82M",
    "ACE-Step/ACE-Step-v1-3.5B",
]
GATED = [  # only if you opt in — needs HF_TOKEN + a one-time license click on each repo's HF page
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
