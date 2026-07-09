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

    MIN_COMPLETED = 100
    MIN_CATEGORY = 20

    try:
        from database import get_recommendation_stats

        rows = get_recommendation_stats()

        total_completed = 0

        for row in rows:
            wins = row["wins"] or 0
            places = row["places"] or 0
            losses = row["losses"] or 0
            total_completed += wins + places + losses

        if total_completed < MIN_COMPLETED:
            print(f"🧠 Learning waiting: {total_completed}/{MIN_COMPLETED} completed results")
            save_settings(settings)
            return settings

        for row in rows:
            rec = row["recommendation"]
            wins = row["wins"] or 0
            places = row["places"] or 0
            losses = row["losses"] or 0

            completed = wins + places + losses
            if completed < MIN_CATEGORY:
                continue

            win_rate = wins / completed
            place_rate = (wins + places) / completed

            if rec == "Strong Single":
                if win_rate < 0.40:
                    settings["strong_single_score"] += 1
                    settings["strong_single_trust"] += 1
                    settings["strong_single_edge"] += 1
                elif win_rate > 0.55:
                    settings["strong_single_score"] = max(68, settings["strong_single_score"] - 0.5)

            if rec == "Multi Anchor":
                if place_rate < 0.65:
                    settings["multi_anchor_score"] += 1
                    settings["multi_anchor_trust"] += 1
                    settings["multi_anchor_edge"] += 1
                elif place_rate > 0.78:
                    settings["multi_anchor_score"] = max(58, settings["multi_anchor_score"] - 0.5)

            if rec == "High Place":
                if place_rate < 0.72:
                    settings["place_confidence"] += 1
                elif place_rate > 0.82:
                    settings["place_confidence"] = max(72, settings["place_confidence"] - 0.5)

        # safety caps
        settings["strong_single_score"] = min(80, max(68, settings["strong_single_score"]))
        settings["strong_single_trust"] = min(80, max(60, settings["strong_single_trust"]))
        settings["strong_single_edge"] = min(25, max(8, settings["strong_single_edge"]))

        settings["multi_anchor_score"] = min(72, max(58, settings["multi_anchor_score"]))
        settings["multi_anchor_trust"] = min(75, max(52, settings["multi_anchor_trust"]))
        settings["multi_anchor_edge"] = min(20, max(6, settings["multi_anchor_edge"]))

        settings["place_confidence"] = min(88, max(72, settings["place_confidence"]))

        save_settings(settings)
        print(f"🧠 Learning updated thresholds: {settings}")
        return settings

    except Exception as e:
        print(f"Learning error: {e}")
        save_settings(settings)
        return settings
