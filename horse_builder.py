from betfair_client import (
    get_australian_horse_markets,
    summarise_horse_markets,
)


def build_horse_bets_message(target_date=None):
    markets = get_australian_horse_markets(target_date)
    return summarise_horse_markets(markets)
