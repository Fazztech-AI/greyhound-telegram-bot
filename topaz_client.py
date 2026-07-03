from datetime import timedelta
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

from topaz import TopazAPI
from config import TOPAZ_API_KEY, AUTHORITY_CODES


def make_topaz():
    return TopazAPI(TOPAZ_API_KEY)


@lru_cache(maxsize=32)
def get_all_races_for_date_cached(target_date_iso):
    topaz = make_topaz()
    from_date = target_date_iso
    # Topaz expects an exclusive-ish next day range for upcoming races
    from datetime import date
    y, m, d = [int(x) for x in target_date_iso.split('-')]
    target_date = date(y, m, d)
    to_date = (target_date + timedelta(days=1)).isoformat()

    all_races = []
    for code in AUTHORITY_CODES:
        try:
            races = topaz.get_races(
                from_date=from_date,
                to_date=to_date,
                owning_authority_code=code,
            )
            if races is None or len(races) == 0:
                continue

            for _, race in races.iterrows():
                r = race.to_dict()
                r["authority"] = code
                all_races.append(r)

        except Exception as e:
            print(f"Race load error {code}: {e}")

    return all_races


def get_all_races_for_date(target_date):
    return list(get_all_races_for_date_cached(target_date.isoformat()))


@lru_cache(maxsize=2000)
def get_runners_for_race_cached(race_id):
    topaz = make_topaz()
    try:
        runners = topaz.get_race_runs(race_id)
        if runners is None or len(runners) == 0:
            return []
        return runners.to_dict("records")
    except Exception as e:
        print(f"Runner load error {race_id}: {e}")
        return []


def get_runners_for_race(race_id):
    return list(get_runners_for_race_cached(race_id))


def get_runners_for_races_parallel(race_ids, max_workers=8):
    """Fetch many race-runner lists concurrently. Much faster than one-by-one."""
    race_ids = [rid for rid in race_ids if rid is not None]
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(get_runners_for_race, rid): rid for rid in race_ids}
        for future in as_completed(future_map):
            rid = future_map[future]
            try:
                results[rid] = future.result()
            except Exception as e:
                print(f"Parallel runner error {rid}: {e}")
                results[rid] = []

    return results
