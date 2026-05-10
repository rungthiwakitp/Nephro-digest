from __future__ import annotations

import json
from pathlib import Path


class ProcessingState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.processed_ids = self._load()

    def _load(self) -> set[str]:
        if not self.path.exists():
            return set()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        ids = data.get("processed_ids", [])
        if not isinstance(ids, list):
            raise ValueError(f"Invalid state file format: {self.path}")
        return set(str(item) for item in ids)

    def seen(self, stable_id: str) -> bool:
        return stable_id in self.processed_ids

    def mark(self, stable_id: str) -> None:
        self.processed_ids.add(stable_id)
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"processed_ids": sorted(self.processed_ids)}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

