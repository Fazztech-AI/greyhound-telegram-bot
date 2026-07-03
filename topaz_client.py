from datetime import timedelta
from topaz import TopazAPI
from config import TOPAZ_API_KEY, AUTHORITY_CODES

def make_topaz():
    return TopazAPI(TOPAZ_API_KEY)

def get_all_races_for_date(target_date):
    topaz = make_topaz()
    from_date = target_date.isoformat()
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

def get_runners_for_race(race_id):
    topaz = make_topaz()
    try:
        runners = topaz.get_race_runs(race_id)
        if runners is None or len(runners) == 0:
            return []
        return runners.to_dict("records")
    except Exception as e:
        print(f"Runner load error {race_id}: {e}")
        return [] 
