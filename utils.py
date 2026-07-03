import re
from datetime import date, timedelta, datetime
import pandas as pd

def is_valid(value):
    return value is not None and not pd.isna(value)

def parse_date_from_text(text: str):
    text = (text or "").lower().strip()
    if "tomorrow" in text:
        return date.today() + timedelta(days=1)

    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return datetime.strptime(match.group(0), "%Y-%m-%d").date()

    return date.today()

def normalise(text: str):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())

def clean_track_text(text: str, target_date):
    text = text or ""
    cleaned = text.replace("tomorrow", "")
    cleaned = cleaned.replace(target_date.isoformat(), "")
    cleaned = re.sub(r"\b\d{1,2}\b", "", cleaned)
    return cleaned.strip()

def chunk_message(text: str, max_len: int = 3900):
    if len(text) <= max_len:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines(True):
        if len(current) + len(line) > max_len:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks
