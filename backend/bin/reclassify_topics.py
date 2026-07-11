#!/usr/bin/env python
"""
One-off: regenerate missing Gemini topics in tops.json without re-embedding.

Usage:
    uv run python bin/reclassify_topics.py
"""

import logging
from pathlib import Path

from langchain.chat_models import init_chat_model

from practicepreach.updater import _update_tops_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

xml_dir = Path("data/xml_updates")
xml_files = sorted(xml_dir.glob("*.xml"))

model = init_chat_model("google_genai:gemini-2.5-flash", thinking_budget=0)
_update_tops_json(xml_files, model)
print("Done.")
