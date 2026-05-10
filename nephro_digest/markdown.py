from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from nephro_digest.feeds import Paper


def slugify(value: str, max_length: int = 80) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return (value[:max_length].strip("-") or "paper")


def filename_for_paper(paper: Paper) -> str:
    published = paper.published or datetime.now(timezone.utc)
    date_part = published.strftime("%Y-%m-%d")
    journal = slugify(paper.journal, 32)
    title = slugify(paper.title)
    short_hash = paper.stable_id[:10]
    return f"{date_part}-{journal}-{title}-{short_hash}.md"


def render_markdown(paper: Paper, summary: str) -> str:
    published = paper.published.isoformat() if paper.published else "Unknown"
    doi_line = f"[{paper.doi}](https://doi.org/{paper.doi})" if paper.doi else "Not found in feed"
    url_line = f"[Article link]({paper.url})" if paper.url else "Not found in feed"
    abstract = paper.abstract or "Not included in RSS feed."

    return (
        f"# {paper.title}\n\n"
        f"- Journal: {paper.journal}\n"
        f"- Published: {published}\n"
        f"- DOI: {doi_line}\n"
        f"- URL: {url_line}\n\n"
        "## Nephrology-Focused Summary\n\n"
        f"{summary.strip()}\n\n"
        "## Abstract\n\n"
        f"{abstract}\n"
    )


def write_summary(output_dir: Path, paper: Paper, markdown: str) -> Path:
    published = paper.published or datetime.now(timezone.utc)
    dated_dir = output_dir / published.strftime("%Y-%m-%d")
    dated_dir.mkdir(parents=True, exist_ok=True)
    path = dated_dir / filename_for_paper(paper)
    path.write_text(markdown, encoding="utf-8")
    return path

