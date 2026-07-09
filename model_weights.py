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

def learn_weights_from_memory():
    weights = load_weights()

    try:
        from learning_history import get_winner_rank_learning

        data = get_winner_rank_learning()
        total = data["total"] or 0

        if total < 100:
            print(f"🧠 Weight learning waiting: {total}/100 races")
            save_weights(weights)
            return weights

        top_rate = data["rank_1"] / total

        if top_rate < 0.35:
            weights["race_trust"] += 0.05
            weights["field_edge"] += 0.05
            weights["score"] = max(0.8, weights["score"] - 0.03)

        elif top_rate > 0.45:
            weights["score"] += 0.03

        for key in weights:
            weights[key] = round(min(1.5, max(0.7, weights[key])), 3)

        save_weights(weights)
        print(f"🧠 Weight learning updated: {weights}")
        return weights

    except Exception as e:
        print(f"Weight learning error: {e}")
        save_weights(weights)
        return weights
