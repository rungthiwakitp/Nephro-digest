from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nephro_digest.feeds import Paper


@dataclass(frozen=True)
class DigestArticle:
    paper: Paper
    article_id: str
    matched_keywords: tuple[str, ...]
    why_this_may_matter: str


def filename_for_digest(run_date: datetime | None = None) -> str:
    date = run_date or datetime.now(timezone.utc)
    return f"{date.strftime('%Y-%m-%d')}-nephrology-digest.md"


def render_daily_digest(
    articles: list[DigestArticle],
    run_date: datetime | None = None,
) -> str:
    date = run_date or datetime.now(timezone.utc)
    lines = [
        f"# Daily Nephrology Digest - {date.strftime('%Y-%m-%d')}",
        "",
        f"Generated: {date.isoformat()}",
        "",
        f"Articles included: {len(articles)}",
        "",
    ]

    if not articles:
        lines.extend(["No new nephrology-related articles found today.", ""])
        return "\n".join(lines).rstrip() + "\n"

    for index, article in enumerate(articles, start=1):
        paper = article.paper
        published = paper.published.isoformat() if paper.published else "Unknown"
        doi_line = (
            f"[{paper.doi}](https://doi.org/{paper.doi})"
            if paper.doi
            else "Not found in feed"
        )
        url_line = f"[Article link]({paper.url})" if paper.url else "Not found in feed"
        abstract = paper.abstract or "Not included in RSS feed."
        matched_keywords = ", ".join(article.matched_keywords) or "None"

        lines.extend(
            [
                f"## {index}. {paper.title}",
                "",
                f"- Journal: {paper.journal}",
                f"- Publication date: {published}",
                f"- DOI: {doi_line}",
                f"- URL: {url_line}",
                f"- Matched keywords: {matched_keywords}",
                "",
                "### Abstract",
                "",
                abstract,
                "",
                "### Why this may matter",
                "",
                article.why_this_may_matter,
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def write_daily_digest(
    output_dir: Path,
    articles: list[DigestArticle],
    run_date: datetime | None = None,
) -> Path:
    date = run_date or datetime.now(timezone.utc)
    dated_dir = output_dir / date.strftime("%Y-%m-%d")
    dated_dir.mkdir(parents=True, exist_ok=True)
    path = dated_dir / filename_for_digest(date)
    path.write_text(render_daily_digest(articles, date), encoding="utf-8")
    return path
