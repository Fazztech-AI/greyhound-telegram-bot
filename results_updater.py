from topaz_client import get_runners_for_race
from database import get_pending_picks, update_pick_result
from learning_history import update_learning_result

def get_runner_name(runner):
    return str(runner.get("dogName") or "").strip().lower()


def get_finish_position(runner):
    possible_keys = [
        "placing",
        "place",
        "position",
        "finishPosition",
        "resultPosition",
        "finishingPosition",
    ]

    for key in possible_keys:
        value = runner.get(key)

        if value is None:
            continue

        try:
            return int(float(value))
        except Exception:
            continue

    return None


def get_starting_price(runner):
    possible_keys = [
        "startingPrice",
        "sp",
        "fixedOdds",
        "winOdds",
    ]

    for key in possible_keys:
        value = runner.get(key)

        if value is None:
            continue

        try:
            return float(value)
        except Exception:
            continue

    return None


def result_from_position(position):
    if position == 1:
        return "Won"

    if position in (2, 3):
        return "Placed"

    return "Lost"


def update_results():
    pending = get_pending_picks()
    updated = 0
    skipped = 0
    reasons = []

    for pick in pending:
        race_id = pick["race_id"]

        if not race_id:
            skipped += 1
            reasons.append(f"#{pick['id']} skipped: no race_id")
            continue

        try:
            runners = get_runners_for_race(race_id)
        except Exception as e:
            skipped += 1
            reasons.append(f"#{pick['id']} skipped: runner load error {e}")
            continue

        if not runners:
            skipped += 1
            reasons.append(f"#{pick['id']} skipped: no runners returned")
            continue

        target_dog = str(pick["dog"] or "").strip().lower()
        matched = False

        for runner in runners:
            if get_runner_name(runner) != target_dog:
                continue

            matched = True
            finish_position = get_finish_position(runner)

            if finish_position is None:
                skipped += 1
                reasons.append(
                    f"#{pick['id']} skipped: dog matched but no finish position. Keys: {list(runner.keys())}"
                )
                break

            result = result_from_position(finish_position)
            starting_price = get_starting_price(runner)

            update_pick_result(
                pick_id=pick["id"],
                result=result,
                finish_position=finish_position,
                starting_price=starting_price,
            )
            update_learning_result(
                race_id=pick["race_id"],
                dog=pick["dog"],
                finish_position=finish_position,
                result=result,
             )

            updated += 1
            break

        if not matched:
            skipped += 1
            reasons.append(f"#{pick['id']} skipped: dog not matched")

    return updated, skipped, reasons[:5]
