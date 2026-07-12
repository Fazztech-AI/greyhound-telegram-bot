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
        settings = json.load(f)

    for key, value in DEFAULT_SETTINGS.items():
        settings.setdefault(key, value)

    return settings


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


def learn_from_results():
    settings = load_settings()

    try:
        from database import get_statistics

        stats = get_statistics()
        completed = stats["completed"] or 0

        print(
            f"🧠 Learning memory updated. "
            f"Completed selections: {completed}. "
            "Automatic threshold changes are currently paused."
        )

        save_settings(settings)
        return settings

    except Exception as e:
        print(f"Learning error: {e}")
        save_settings(settings)
        return settings
