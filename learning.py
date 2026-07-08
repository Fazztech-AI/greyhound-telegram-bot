import json
from pathlib import Path

SETTINGS_FILE = Path("learning.json")


DEFAULT_SETTINGS = {
    "strong_single_score": 70,
    "strong_single_margin": 8,
    "strong_single_trust": 65,
    "strong_single_edge": 10,

    "multi_anchor_score": 60,
    "multi_anchor_margin": 5,
    "multi_anchor_trust": 55,
    "multi_anchor_edge": 7,

    "place_confidence": 75,
}


def load_settings():
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
