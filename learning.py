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
    """
    Safe early learning engine.

    It does NOT change thresholds until there are enough completed results.
    This prevents the bot overreacting to a tiny sample size.
    """
    settings = load_settings()

    # Minimum data before the bot is allowed to self-adjust
    minimum_completed = 100

    try:
        from database import get_threshold_report

        row = get_threshold_report()
        completed = row["completed"] or 0

        if completed < minimum_completed:
            print(
                f"🧠 Learning skipped. "
                f"Completed results: {completed}/{minimum_completed}"
            )
            save_settings(settings)
            return settings

        avg_score = row["avg_score"] or settings["strong_single_score"]
        avg_margin = row["avg_margin"] or settings["strong_single_margin"]
        avg_trust = row["avg_trust"] or settings["strong_single_trust"]
        avg_edge = row["avg_edge"] or settings["strong_single_edge"]

        # Move thresholds slowly toward winning averages
        settings["strong_single_score"] = round(
            (settings["strong_single_score"] * 0.9) + (avg_score * 0.1),
            1,
        )

        settings["strong_single_margin"] = round(
            (settings["strong_single_margin"] * 0.9) + (avg_margin * 0.1),
            1,
        )

        settings["strong_single_trust"] = round(
            (settings["strong_single_trust"] * 0.9) + (avg_trust * 0.1),
            1,
        )

        settings["strong_single_edge"] = round(
            (settings["strong_single_edge"] * 0.9) + (avg_edge * 0.1),
            1,
        )

        save_settings(settings)

        print(f"🧠 Learning updated thresholds: {settings}")
        return settings

    except Exception as e:
        print(f"Learning error: {e}")
        save_settings(settings)
        return settings
