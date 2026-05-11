from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from nephro_digest.feeds import Paper


class ProcessingState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.seen_ids, self.last_updated = self._load()

    def _load(self) -> tuple[set[str], str | None]:
        if not self.path.exists():
            return set(), None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        ids = data.get("seen_articles", data.get("processed_ids", []))
        if not isinstance(ids, list):
            raise ValueError(f"Invalid state file format: {self.path}")
        last_updated = data.get("last_updated")
        if last_updated is not None and not isinstance(last_updated, str):
            raise ValueError(f"Invalid last_updated value in state file: {self.path}")
        return set(str(item) for item in ids), last_updated

    def seen(self, article_id: str) -> bool:
        return article_id in self.seen_ids

    def mark_many(
        self,
        article_ids: list[str],
        updated_at: datetime | None = None,
    ) -> None:
        self.seen_ids.update(article_ids)
        self.save(updated_at)

    def save(self, updated_at: datetime | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if updated_at is not None:
            self.last_updated = updated_at.isoformat()
        payload = {
            "seen_articles": sorted(self.seen_ids),
            "last_updated": self.last_updated,
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def article_id_for_paper(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{normalize_doi(paper.doi)}"
    if paper.url:
        return f"url:{normalize_url(paper.url)}"
    return f"title:{normalize_title(paper.title)}"


def normalize_doi(value: str) -> str:
    return value.strip().lower()


def normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def normalize_title(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()
