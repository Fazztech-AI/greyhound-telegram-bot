import json
import os
from typing import Any

import requests

BASE_URL = "https://puntersedge.online/api/v1"
API_KEY = os.getenv("PUNTERSEDGE_API_KEY", "").strip()


class PuntersEdgeError(Exception):
    pass


def _headers() -> dict[str, str]:
    if not API_KEY:
        raise PuntersEdgeError(
            "PUNTERSEDGE_API_KEY is missing from Railway variables."
        )

    print(
        "PuntersEdge key loaded:",
        bool(API_KEY),
        "length:",
        len(API_KEY),
        "start:",
        API_KEY[:4],
        "end:",
        API_KEY[-4:],
    )

    return {
        "X-API-Key": API_KEY,
        "Accept": "application/json",
        "User-Agent": "GreyhoundTelegramBot/1.0",
    }


def _get(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{BASE_URL}{endpoint}"

    try:
        response = requests.get(
            url,
            headers=_headers(),
            params=params,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise PuntersEdgeError(f"Connection error: {exc}") from exc

    if response.status_code != 200:
        body = response.text[:1000]
        raise PuntersEdgeError(
            f"PuntersEdge returned HTTP {response.status_code}: {body}"
        )

    try:
        data = response.json()

        # Temporary debug for Belmont R7
        if endpoint == "/racing/next-to-go":
            races = (
                data
                if isinstance(data, list)
                else data.get("races", data.get("data", []))
            )

            for race in races:
                if (
                    str(race.get("venue", "")).lower() == "belmont"
                    and int(race.get("race_number", 0)) == 7
                ):
                    print("\n========== BELMONT R7 ==========")
                    print(json.dumps(race, indent=2))
                    print("========== END BELMONT R7 ==========\n")

        return data

    except ValueError as exc:
        raise PuntersEdgeError(
            f"PuntersEdge returned invalid JSON: {response.text[:1000]}"
        ) from exc


def check_usage() -> Any:
    """Return API usage information."""
    return _get("/usage")


def get_horse_races(limit: int = 10) -> Any:
    """Return upcoming horse races."""
    return _get(
        "/racing/next-to-go",
        params={
            "categories": "horse",
            "limit": limit,
        },
    )


def get_horse_events(hours_ahead: int = 24) -> Any:
    """Return upcoming horse racing events."""
    return _get(
        "/racing/events",
        params={
            "category": "horse",
            "hours_ahead": hours_ahead,
        },
    )
