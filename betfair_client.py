from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from config import BETFAIR_APP_KEY, BETFAIR_SESSION_TOKEN


MELBOURNE_TZ = ZoneInfo("Australia/Melbourne")

BETFAIR_API_URL = (
    "https://api-au.betfair.com/exchange/betting/json-rpc/v1"
)

HORSE_RACING_EVENT_TYPE_ID = "7"


class BetfairAPIError(RuntimeError):
    pass


def _require_credentials():
    if not BETFAIR_APP_KEY:
        raise BetfairAPIError(
            "BETFAIR_APP_KEY is missing from Railway Variables."
        )

    if not BETFAIR_SESSION_TOKEN:
        raise BetfairAPIError(
            "BETFAIR_SESSION_TOKEN is missing or expired."
        )


def _headers():
    _require_credentials()

    return {
        "X-Application": BETFAIR_APP_KEY,
        "X-Authentication": BETFAIR_SESSION_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _betfair_request(method, params):
    payload = {
        "jsonrpc": "2.0",
        "method": f"SportsAPING/v1.0/{method}",
        "params": params,
        "id": 1,
    }

    try:
        response = requests.post(
            BETFAIR_API_URL,
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise BetfairAPIError(
            f"Betfair connection error: {exc}"
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise BetfairAPIError(
            f"Betfair returned invalid JSON: {response.text[:500]}"
        ) from exc

    if "error" in data:
        error = data["error"]
        message = error.get("message", "Unknown Betfair error")
        details = error.get("data")

        raise BetfairAPIError(
            f"{message}: {details}"
        )

    return data.get("result", [])


def _utc_range_for_melbourne_date(target_date):
    """
    Convert one Melbourne calendar day into Betfair's UTC time range.
    """
    local_start = datetime.combine(
        target_date,
        time.min,
        tzinfo=MELBOURNE_TZ,
    )

    local_end = local_start + timedelta(days=1)

    return (
        local_start.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        local_end.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    )


def get_australian_horse_markets(target_date=None, max_results=1000):
    """
    Return Australian horse-racing WIN markets for one Melbourne date.

    Includes:
    - meeting/event information
    - market start time
    - runners
    - horse runner metadata when supplied by Betfair
    """
    if target_date is None:
        target_date = datetime.now(MELBOURNE_TZ).date()

    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    from_time, to_time = _utc_range_for_melbourne_date(target_date)

    params = {
        "filter": {
            "eventTypeIds": [HORSE_RACING_EVENT_TYPE_ID],
            "marketCountries": ["AU"],
            "marketTypeCodes": ["WIN"],
            "marketStartTime": {
                "from": from_time,
                "to": to_time,
            },
        },
        "marketProjection": [
            "EVENT",
            "MARKET_START_TIME",
            "MARKET_DESCRIPTION",
            "RUNNER_DESCRIPTION",
            "RUNNER_METADATA",
        ],
        "sort": "FIRST_TO_START",
        "maxResults": str(max_results),
        "locale": "en",
    }

    return _betfair_request(
        "listMarketCatalogue",
        params,
    )


def get_market_prices(market_ids):
    """
    Return delayed exchange prices for the supplied market IDs.
    """
    market_ids = [
        str(market_id)
        for market_id in market_ids
        if market_id
    ]

    if not market_ids:
        return []

    params = {
        "marketIds": market_ids,
        "priceProjection": {
            "priceData": [
                "EX_BEST_OFFERS",
            ],
            "virtualise": True,
        },
    }

    return _betfair_request(
        "listMarketBook",
        params,
    )


def get_today_horse_markets():
    return get_australian_horse_markets(
        datetime.now(MELBOURNE_TZ).date()
    )


def summarise_horse_markets(markets):
    """
    Temporary readable output used to confirm the API works.
    """
    if not markets:
        return (
            "🐎 BETFAIR HORSE TEST\n\n"
            "No Australian horse WIN markets were returned."
        )

    lines = [
        "🐎 BETFAIR HORSE TEST",
        "",
        f"Markets returned: {len(markets)}",
        "",
    ]

    for market in markets[:20]:
        event = market.get("event") or {}

        venue = (
            event.get("venue")
            or event.get("name")
            or "Unknown meeting"
        )

        market_name = market.get("marketName", "Unknown race")
        start_time = market.get("marketStartTime", "")
        runners = market.get("runners") or []

        lines.append(
            f"• {venue} — {market_name} — "
            f"{start_time} — {len(runners)} runners"
        )

    if len(markets) > 20:
        lines.append("")
        lines.append(
            f"...and {len(markets) - 20} more markets."
        )

    return "\n".join(lines)[:4000]
