import json
from pathlib import Path

WEIGHTS_FILE = Path("model_weights.json")

DEFAULT_WEIGHTS = {
    "score": 1.0,
    "race_trust": 1.0,
    "field_edge": 1.0,
    "margin": 1.0,
}


def load_weights():
    if not WEIGHTS_FILE.exists():
        save_weights(DEFAULT_WEIGHTS)
        return DEFAULT_WEIGHTS.copy()

    with open(WEIGHTS_FILE, "r") as f:
        weights = json.load(f)

    for key, value in DEFAULT_WEIGHTS.items():
        weights.setdefault(key, value)

    return weights


def save_weights(weights):
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, indent=4)


def weighted_confidence(score, race_trust, field_edge, margin):
    weights = load_weights()

    final = (
        score * weights["score"]
        + race_trust * weights["race_trust"]
        + field_edge * weights["field_edge"]
        + margin * weights["margin"]
    )

    divisor = (
        weights["score"]
        + weights["race_trust"]
        + weights["field_edge"]
        + weights["margin"]
    )

    return round(final / divisor, 1)
