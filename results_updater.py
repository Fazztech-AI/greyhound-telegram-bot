from datetime import datetime
from topaz_client import get_runners_for_race
from database import (
    get_pending_picks,
    update_pick_result,
)


def update_results():
    pending = get_pending_picks()

    updated = 0

    for pick in pending:
        race_id = pick["race_id"]

        try:
            runners = get_runners_for_race(race_id)
        except Exception:
            continue

        for runner in runners:
            if runner.get("dogName") != pick["dog"]:
                continue

            placing = runner.get("placing")

            if placing is None:
                continue

            if placing == 1:
                result = "WIN"
                won = 1
                placed = 1
            elif placing <= 3:
                result = "PLACE"
                won = 0
                placed = 1
            else:
                result = "LOSS"
                won = 0
                placed = 0

            update_pick_result(
                pick_id=pick["id"],
                result=result,
                finish_position=placing,
                won=won,
                placed=placed,
                starting_price=runner.get("startingPrice"),
                updated_at=datetime.now().isoformat(),
            )

            updated += 1

            break

    return updated
