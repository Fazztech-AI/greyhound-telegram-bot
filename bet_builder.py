import re

from topaz_client import (
    get_all_races_for_date,
    get_runners_for_races_parallel,
)

from scorer import score_runner

from utils import (
    normalise,
    melbourne_today,
)

from race_filters import (
    should_scan_race,
    active_runners_only,
)

def get_track_name(race, runners=None):
    if runners:
        track = runners[0].get("track")
        if track:
            return str(track)

    name = str(race.get("name", ""))
    match = re.search(r"@([A-Z]+)", name)

    if match:
        return match.group(1)

    return "Unknown Track"


def track_matches(track_name, search):
    return normalise(search) in normalise(track_name)


def build_meeting_track_map(races):

    meeting_first_race = {}

    for race in races:
        meeting_id = race.get("meetingId")

        if meeting_id not in meeting_first_race:
            meeting_first_race[meeting_id] = race

    first_race_ids = [
        race.get("raceId")
        for race in meeting_first_race.values()
    ]

    runners_by_race = get_runners_for_races_parallel(
        first_race_ids,
        max_workers=8,
    )

    track_map = {}

    for meeting_id, race in meeting_first_race.items():

        runners = runners_by_race.get(
            race.get("raceId"),
            [],
        )

        track_map[meeting_id] = get_track_name(
            race,
            runners,
        )

    return track_map


def scan_ranked(target_date=None, track_search=None):

    if target_date is None:
        target_date = melbourne_today()

    races = get_all_races_for_date(target_date)

    meeting_track_map = build_meeting_track_map(races)

    filtered = []

    for race in races:

        if not should_scan_race(race, target_date):
            continue

        if track_search:

            track = meeting_track_map.get(
                race.get("meetingId"),
                "Unknown Track",
            )

            if not track_matches(track, track_search):
                continue

        filtered.append(race)

    race_ids = [
        race.get("raceId")
        for race in filtered
    ]

    runners_by_race = get_runners_for_races_parallel(
        race_ids,
        max_workers=8,
    )

    ranked = []

    for race in filtered:

        runners = runners_by_race.get(
            race.get("raceId"),
            [],
        )

        active = active_runners_only(runners)

        if len(active) < 4:
            continue

        track = get_track_name(race, active)

        if track == "Unknown Track":
            track = meeting_track_map.get(
                race.get("meetingId"),
                "Unknown Track",
            )

        scored = []

        for runner in active:

            score, pros, warnings = score_runner(
                runner,
                active,
            )

            scored.append(
                (
                    score,
                    runner,
                    pros,
                    warnings,
                )
            )

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        best_score, best_runner, pros, warnings = scored[0]

        second_score = (
            scored[1][0]
            if len(scored) > 1
            else 0
        )

        ranked.append(
            {
                "score": best_score,
                "margin": round(
                    best_score - second_score,
                    1,
                ),
                "race": race,
                "runner": best_runner,
                "runners": active,
                "pros": pros,
                "warnings": warnings,
                "track": track,
                "field_size": len(active),
                "full_rankings": scored,
            }
        )

    ranked.sort(
        key=lambda x: (
            x["score"],
            x["margin"],
        ),
        reverse=True,
    )

    return ranked
    from strategy import (
    betting_plan,
    daily_summary,
)

from formatter import (
    format_daily_plan,
    format_track_list,
    format_race_breakdown,
)


def format_runner_short(runner):
    box = runner.get("boxNumber") or runner.get("rugNumber") or "?"
    dog = runner.get("dogName", "Unknown Dog")
    return f"Box {box} {dog}"


def build_best_bets_message(target_date=None, track_search=None):

    if target_date is None:
        target_date = melbourne_today()

    ranked = scan_ranked(
        target_date,
        track_search,
    )

    if not ranked:

        if track_search:
            return (
                f"No upcoming races found for "
                f"'{track_search}' on {target_date}."
            )

        return (
            f"No upcoming race data found "
            f"for {target_date}."
        )

    summary = daily_summary(ranked)

    return format_daily_plan(
        summary,
        betting_plan,
        target_date,
    )


def build_tracks_message(target_date=None):

    if target_date is None:
        target_date = melbourne_today()

    races = get_all_races_for_date(target_date)

    meeting_track_map = build_meeting_track_map(races)

    tracks = {}

    for race in races:

        if not should_scan_race(race, target_date):
            continue

        track = meeting_track_map.get(
            race.get("meetingId"),
            "Unknown Track",
        )

        tracks.setdefault(track, 0)
        tracks[track] += 1

    if not tracks:
        return (
            f"No upcoming tracks found "
            f"for {target_date}."
        )

    return format_track_list(
        tracks,
        target_date,
    )


def build_race_message(
    track_search,
    race_number,
    target_date=None,
):

    if target_date is None:
        target_date = melbourne_today()

    ranked = scan_ranked(
        target_date,
        track_search,
    )

    race_pick = None

    for pick in ranked:

        if (
            str(
                pick["race"].get(
                    "raceNumber",
                    "",
                )
            )
            == str(race_number)
        ):

            race_pick = pick
            break

    if race_pick is None:

        return (
            f"No upcoming race found for "
            f"{track_search} R{race_number} "
            f"on {target_date}."
        )

    return format_race_breakdown(
        race_pick,
    )
