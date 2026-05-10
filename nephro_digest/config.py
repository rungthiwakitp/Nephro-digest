from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_FEEDS: dict[str, list[str]] = {
    "KI": ["https://www.kidney-international.org/current.rss"],
    "CJASN": [
        "https://journals.lww.com/CJASN/_layouts/15/OAKS.Journals/feed.aspx?FeedType=CurrentIssue"
    ],
    "JASN": [
        "https://journals.lww.com/JASN/_layouts/15/OAKS.Journals/feed.aspx?FeedType=CurrentIssue"
    ],
    "NEJM": ["https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss"],
    "Transplantation": [
        "https://journals.lww.com/transplantjournal/_layouts/15/OAKS.Journals/feed.aspx?FeedType=CurrentIssue"
    ],
    "AJT": ["https://www.amjtransplant.org/current.rss"],
}


@dataclass(frozen=True)
class Settings:
    feeds: dict[str, list[str]]
    output_dir: Path
    state_file: Path
    openai_model: str
    max_output_tokens: int
    max_papers_per_run: int
    lookback_days: int | None
    google_drive_folder_id: str | None
    skip_google_drive: bool
    dry_run: bool


def _bool_from_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _optional_positive_int_from_env(name: str, default: int | None) -> int | None:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    return parsed if parsed > 0 else None


def _normalize_feed_config(raw: Any) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        raise ValueError("FEED_URLS_JSON must be a JSON object")

    feeds: dict[str, list[str]] = {}
    for journal, urls in raw.items():
        if isinstance(urls, str):
            feeds[str(journal)] = [urls]
        elif isinstance(urls, list) and all(isinstance(url, str) for url in urls):
            feeds[str(journal)] = urls
        else:
            raise ValueError(
                "FEED_URLS_JSON values must be feed URL strings or lists of strings"
            )

    return feeds


def load_settings() -> Settings:
    raw_feeds = os.getenv("FEED_URLS_JSON")
    feeds = DEFAULT_FEEDS if raw_feeds is None else _normalize_feed_config(json.loads(raw_feeds))

    return Settings(
        feeds=feeds,
        output_dir=Path(os.getenv("OUTPUT_DIR", "summaries")),
        state_file=Path(os.getenv("STATE_FILE", ".state/processed.json")),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.2"),
        max_output_tokens=_int_from_env("OPENAI_MAX_OUTPUT_TOKENS", 450),
        max_papers_per_run=_int_from_env("MAX_PAPERS_PER_RUN", 50),
        lookback_days=_optional_positive_int_from_env("LOOKBACK_DAYS", 14),
        google_drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
        skip_google_drive=_bool_from_env("SKIP_GOOGLE_DRIVE", False),
        dry_run=_bool_from_env("DRY_RUN", False),
    )
