import re

from telegram import Update
from telegram.ext import ContextTypes

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
)

from database import (
    update_result,
)

async def send_long(update: Update, text: str):
    for chunk in chunk_message(text):
        await update.message.reply_text(chunk)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound AI v1.0 online.\n\n"
        "Commands:\n"
        "/scan\n"
        "/tracks\n"
        "/tracks tomorrow\n"
        "/track Geelong\n"
        "/track The Meadows tomorrow\n"
        "/race Geelong 5\n"
        "/race The Meadows 8\n\n"
        "You can also just type a track name."
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning and rating all races...")
    try:
        await send_long(update, build_best_bets_message())
    except Exception as e:
        await update.message.reply_text(f"Scanner error:\n{e}")

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
        await update.message.reply_text("Example: /track Geelong or /track The Meadows tomorrow")
        return

    target_date = parse_date_from_text(text)
    clean_track = clean_track_text(text, target_date)

    await update.message.reply_text(f"🔍 Scanning {clean_track} for {target_date}...")
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

    await update.message.reply_text(f"🔍 Loading {clean_track} R{race_number} for {target_date}...")
    try:
        await send_long(update, build_race_message(clean_track, race_number, target_date))
    except Exception as e:
        await update.message.reply_text(f"Race scanner error:\n{e}")

async def natural_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    target_date = parse_date_from_text(text)
    clean_track = clean_track_text(text, target_date)

    await update.message.reply_text(f"🔍 Checking {clean_track} for {target_date}...")
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
