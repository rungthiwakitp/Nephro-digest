from __future__ import annotations

import hashlib
import re
import calendar
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable

import feedparser


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
REQUEST_HEADERS = {
    "User-Agent": (
        "nephro-digest/1.0 (+https://github.com/) "
        "Mozilla/5.0 RSS reader"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(part.strip() for part in self.parts if part.strip())


@dataclass(frozen=True)
class Paper:
    journal: str
    title: str
    abstract: str
    doi: str | None
    url: str
    published: datetime | None
    source_id: str

    @property
    def stable_id(self) -> str:
        identifier = self.doi or self.source_id or self.url or self.title
        return hashlib.sha256(identifier.lower().encode("utf-8")).hexdigest()


def html_to_text(value: str | None) -> str:
    if not value:
        return ""
    parser = _HTMLTextExtractor()
    parser.feed(value)
    text = parser.text() or value
    return re.sub(r"\s+", " ", unescape(text)).strip()


def fetch_papers(feeds: dict[str, list[str]]) -> list[Paper]:
    papers: list[Paper] = []
    for journal, urls in feeds.items():
        for url in urls:
            parsed = feedparser.parse(url, request_headers=REQUEST_HEADERS)
            if parsed.bozo:
                reason = getattr(parsed, "bozo_exception", "unknown RSS parse error")
                print(f"Warning: feed parse issue for {journal} ({url}): {reason}")

            for entry in parsed.entries:
                paper = entry_to_paper(journal, entry)
                if paper:
                    papers.append(paper)

    papers.sort(
        key=lambda paper: paper.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return papers


def entry_to_paper(journal: str, entry: Any) -> Paper | None:
    title = html_to_text(entry.get("title"))
    if not title:
        return None

    abstract = first_nonempty(
        html_to_text(content.get("value"))
        for content in entry.get("content", [])
        if isinstance(content, dict)
    )
    if not abstract:
        abstract = html_to_text(entry.get("summary") or entry.get("description"))

    doi = extract_doi(entry)
    url = extract_url(entry, doi)
    published = extract_date(entry)
    source_id = str(entry.get("id") or entry.get("guid") or url or title)

    return Paper(
        journal=journal,
        title=title,
        abstract=abstract,
        doi=doi,
        url=url,
        published=published,
        source_id=source_id,
    )


def first_nonempty(values: Iterable[str]) -> str:
    for value in values:
        if value:
            return value
    return ""


def extract_url(entry: Any, doi: str | None) -> str:
    link = entry.get("link")
    if link:
        return str(link)

    for candidate in entry.get("links", []):
        if isinstance(candidate, dict) and candidate.get("href"):
            return str(candidate["href"])

    if doi:
        return f"https://doi.org/{doi}"
    return ""


def extract_date(entry: Any) -> datetime | None:
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed_time:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=timezone.utc)


def extract_doi(entry: Any) -> str | None:
    explicit_keys = (
        "doi",
        "prism_doi",
        "dc_identifier",
        "dc:identifier",
        "identifier",
        "id",
        "guid",
        "link",
        "summary",
        "description",
    )

    candidates: list[str] = []
    for key in explicit_keys:
        value = entry.get(key)
        if value:
            candidates.append(str(value))

    for key, value in entry.items():
        if "doi" in str(key).lower() and value:
            candidates.append(str(value))

    for candidate in candidates:
        match = DOI_RE.search(candidate)
        if match:
            return match.group(0).rstrip(".,);]")

    return None
