from datetime import datetime
from zoneinfo import ZoneInfo

from utils import melbourne_today

MELBOURNE_TZ = ZoneInfo("Australia/Melbourne")


def melbourne_now():
    return datetime.now(MELBOURNE_TZ)


def parse_race_start(race):
    """
    Converts Topaz raceStart into Melbourne time.
    Returns None if unavailable.
    """
    raw = race.get("raceStart")

    if not raw:
        return None

    try:
        raw = str(raw).replace("Z", "+00:00")
        return datetime.fromisoformat(raw).astimezone(MELBOURNE_TZ)
    except Exception:
        return None


def race_is_on_target_date(race, target_date):
    """
    Only include races that belong to the requested Melbourne date.
    """

    start = parse_race_start(race)

    if start is None:
        return True

    return start.date() == target_date


def race_has_started(race, target_date):
    """
    Skip races already started when scanning today's races.
    """

    if target_date != melbourne_today():
        return False

    start = parse_race_start(race)

    if start is None:
        return False

    return start <= melbourne_now()


def race_is_resulted(race):
    """
    True if race result already exists.
    """

    return (
        race.get("isRaceResultEntered") is True
        or race.get("raceResultEntered") is True
    )


def race_is_abandoned(race):
    """
    True if race has been abandoned.
    """

    return (
        race.get("abandoned") is True
        or race.get("isAbandoned") is True
    )


def race_is_valid(race):
    """
    Race can be analysed.
    """

    return (
        not race_is_resulted(race)
        and not race_is_abandoned(race)
    )


def active_runners_only(runners):
    """
    Remove scratchings and late scratchings.
    """

    return [
        runner
        for runner in runners
        if not runner.get("scratched", False)
        and not runner.get("isLateScratching", False)
    ]


def valid_field(active_runners):
    """
    Ignore races with fewer than four active runners.
    """

    return len(active_runners) >= 4


def should_scan_race(race, target_date):
    """
    Master filter for every race.
    """

    if not race_is_valid(race):
        return False

    if not race_is_on_target_date(race, target_date):
        return False

    if race_has_started(race, target_date):
        return False

    return True
