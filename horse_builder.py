from topaz_client import make_topaz
from utils import melbourne_today
from datetime import timedelta


def build_horse_bets_message(target_date=None):
    if target_date is None:
        target_date = melbourne_today()

    topaz = make_topaz()

    tomorrow = target_date + timedelta(days=1)

    try:
        races = topaz.get_races(
            from_date=target_date.isoformat(),
            to_date=tomorrow.isoformat(),
            owning_authority_code="RV",
        )

        if races is None or len(races) == 0:
            return "No horse races returned for authority RV."

        return str(races.head())

    except Exception as e:
        return f"Error: {e}"
