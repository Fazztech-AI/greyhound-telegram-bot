import re

from telegram import Update
from telegram.ext import ContextTypes
from horse_builder import build_horse_bets_message
from telegram.ext import CommandHandler

from horse_client import check_usage, get_horse_races, PuntersEdgeError
from bet_builder import (
    build_best_bets_message,
    build_tracks_message,
    build_race_message,
)

from utils import (
    parse_date_from_text,
    clean_track_text,
    chunk_message,
    melbourne_today,
)

from history import (
    build_history_message,
    build_statistics_message,
    build_recommendation_stats_message,
    build_score_band_stats_message,
    build_track_stats_message,
    build_box_stats_message,
    build_threshold_report_message,
    build_memory_stats_message,
)

from database import (
    update_result,
)

from results_updater import update_results


async def send_long(update: Update, text: str):
    for chunk in chunk_message(text):
        await update.message.reply_text(chunk)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏇 Australian Racing AI v1.0\n\n"

        "🐕 GREYHOUNDS\n"
        "/scan\n"
        "/scan greys\n"
        "/tracks\n"
        "/tracks tomorrow\n"
        "/track Geelong\n"
        "/track The Meadows tomorrow\n"
        "/race Geelong 5\n"
        "/race The Meadows 8\n\n"

        "🐎 HORSES\n"
        "/scan horses (Coming Soon)\n\n"

        "💬 You can also just type a greyhound track name."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = context.args[0].strip().lower() if context.args else "greys"

    greyhound_names = {
        "grey",
        "greys",
        "greyhound",
        "greyhounds",
        "dogs",
    }

    horse_names = {
        "horse",
        "horses",
        "thoroughbred",
        "thoroughbreds",
    }

    if code in greyhound_names:
        await update.message.reply_text(
            "🔍 Scanning and rating Australian greyhound races..."
        )

        try:
            await send_long(
                update,
                build_best_bets_message(),
            )
        except Exception as e:
            await update.message.reply_text(
                f"Greyhound scanner error:\n{e}"
            )

        return

    if code in horse_names:
        await update.message.reply_text(
            "🔍 Scanning Australian horse races..."
        )

        try:
            await send_long(
                update,
                build_horse_bets_message(),
            )
        except Exception as e:
            await update.message.reply_text(
                f"Horse scanner error:\n{e}"
            )

        return

    await update.message.reply_text(
        "Use:\n"
        "/scan greys\n"
        "/scan horses"
    )

async def tracks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    target_date = parse_date_from_text(text) if text else melbourne_today()

    await update.message.reply_text("🔍 Loading available tracks...")
    try:
        await send_long(update, build_tracks_message(target_date))
    except Exception as e:
        await update.message.reply_text(f"Tracks error:\n{e}")


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()

    if not text:
        await update.message.reply_text(
            "Example: /track Geelong or /track The Meadows tomorrow"
        )
        return

    target_date = parse_date_from_text(text)
    clean_track = clean_track_text(text, target_date)

    await update.message.reply_text(
        f"🔍 Scanning {clean_track} for {target_date}..."
    )

    try:
        await send_long(update, build_best_bets_message(target_date, clean_track))
    except Exception as e:
        await update.message.reply_text(f"Track scanner error:\n{e}")


async def race_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    match = re.search(r"\b(\d{1,2})\b", text)

    if not match:
        await update.message.reply_text("Example: /race Geelong 5")
        return

    race_number = match.group(1)
    target_date = parse_date_from_text(text)
    clean_track = clean_track_text(text, target_date)

    if not clean_track:
        await update.message.reply_text("Example: /race Geelong 5")
        return

    await update.message.reply_text(
        f"🔍 Loading {clean_track} R{race_number} for {target_date}..."
    )

    try:
        await send_long(
            update,
            build_race_message(clean_track, race_number, target_date),
        )
    except Exception as e:
        await update.message.reply_text(f"Race scanner error:\n{e}")


async def natural_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    target_date = parse_date_from_text(text)
    clean_track = clean_track_text(text, target_date)

    await update.message.reply_text(
        f"🔍 Checking {clean_track} for {target_date}..."
    )

    try:
        await send_long(update, build_best_bets_message(target_date, clean_track))
    except Exception as e:
        await update.message.reply_text(f"Message scanner error:\n{e}")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await send_long(update, build_history_message())
    except Exception as e:
        await update.message.reply_text(f"History error:\n{e}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.args:
            arg = context.args[0].lower()

            if arg in ["recommendations", "recs", "types"]:
                await update.message.reply_text(
                    build_recommendation_stats_message()
                )
                return

            if arg in ["scores", "score", "bands"]:
                await update.message.reply_text(
                    build_score_band_stats_message()
                )
                return

            if arg in ["tracks", "track"]:
                await update.message.reply_text(
                    build_track_stats_message()
                )
                return

            if arg in ["boxes", "box"]:
                await update.message.reply_text(
                    build_box_stats_message()
                )
                return

            if arg in ["learning", "learn", "thresholds"]:
                await update.message.reply_text(
                    build_threshold_report_message()
                )
                return
            if arg in ["memory", "brain"]:
                await update.message.reply_text(build_memory_stats_message())
                return
        await update.message.reply_text(build_statistics_message())

    except Exception as e:
        await update.message.reply_text(f"Stats error:\n{e}")


async def record_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Example:\n"
            "/record 12 Won 2.30\n"
            "/record 13 Lost\n"
            "/record 14 Placed 1.65"
        )
        return

    try:
        bet_id = int(context.args[0])
        result = context.args[1].capitalize()

        price = None
        if len(context.args) >= 3:
            price = float(context.args[2])

        update_result(bet_id, result, price)

        await update.message.reply_text("✅ Result recorded.")

    except Exception as e:
        await update.message.reply_text(f"Record error:\n{e}")


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        updated, skipped, reasons = update_results()

        msg = (
            f"✅ Results update complete.\n"
            f"Updated: {updated}\n"
            f"Skipped: {skipped}"
        )

        if reasons:
            msg += "\n\nReasons:\n"
            msg += "\n".join(str(r) for r in reasons)

        await update.message.reply_text(msg[:4000])

    except Exception as e:
        await update.message.reply_text(f"Update error:\n{e}")

async def debug_race_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /debugrace 123456")
        return

    race_id = context.args[0]

    try:
        runners = debug_race_runs(race_id)
        await update.message.reply_text(
            f"Debug printed {len(runners)} runners to Railway logs."
        )
    except Exception as e:
        await update.message.reply_text(f"Debug race error:\n{e}")

async def test_horses(update, context):
    await update.message.reply_text("🐎 Testing PuntersEdge horse API...")

    try:
        usage = check_usage()
        races = get_horse_races(limit=5)

        print("PUNTERSEDGE USAGE:")
        print(usage)

        print("PUNTERSEDGE HORSE DATA:")
        print(races)

        await update.message.reply_text(
            "✅ PuntersEdge API connected successfully.\n"
            "Check Railway logs for the raw horse-racing data."
        )

    except PuntersEdgeError as exc:
        print(f"PUNTERSEDGE ERROR: {exc}")

        await update.message.reply_text(
            f"❌ PuntersEdge API error:\n{exc}"
        )

    except Exception as exc:
        print(f"UNEXPECTED HORSE TEST ERROR: {exc}")

        await update.message.reply_text(
            f"❌ Unexpected error:\n{exc}"
        )
