import os
from typing import Any

import requests


BASE_URL = "https://puntersedge.online/api/v1"
API_KEY = os.getenv("PUNTERSEDGE_API_KEY")


class PuntersEdgeError(Exception):
    pass


def _headers() -> dict[str, str]:
    if not API_KEY:
        raise PuntersEdgeError(
            "PUNTERSEDGE_API_KEY is missing from Railway variables."
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
        return response.json()
    except ValueError as exc:
        raise PuntersEdgeError(
            f"PuntersEdge returned invalid JSON: {response.text[:1000]}"
        ) from exc


def check_usage() -> Any:
    """Check remaining monthly API credits."""
    return _get("/usage")


def get_horse_races(limit: int = 10) -> Any:
    """
    Return upcoming horse races with runners and available prices.

    The next-to-go endpoint costs 2 credits per request.
    """
    return _get(
        "/racing/next-to-go",
        params={
            "categories": "horse",
            "limit": limit,
        },
    )


def get_horse_events(hours_ahead: int = 24) -> Any:
    """
    Return upcoming horse-racing events.

    This endpoint costs 1 credit per request.
    """
    return _get(
        "/racing/events",
        params={
            "category": "horse",
            "hours_ahead": hours_ahead,
        },
    )
