from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone

from nephro_digest.config import load_settings
from nephro_digest.feeds import Paper, fetch_papers
from nephro_digest.markdown import DigestArticle, filename_for_digest, write_daily_digest
from nephro_digest.state import ProcessingState, article_id_for_paper


NON_ARTICLE_TITLES = {
    "table of contents",
    "subscription information",
    "editorial board",
    "outside front cover",
    "inside front cover",
}

NEPHROLOGY_KEYWORDS = (
    "kidney",
    "renal",
    "nephrology",
    "CKD",
    "AKI",
    "dialysis",
    "transplant",
    "glomerular",
    "proteinuria",
    "ESRD",
    "IgA nephropathy",
    "hemodialysis",
    "peritoneal dialysis",
    "nephrotic syndrome",
)

KEYWORD_NOTE_TOPICS = {
    "kidney": "kidney disease or kidney function",
    "renal": "kidney disease or kidney function",
    "nephrology": "nephrology practice or research",
    "CKD": "chronic kidney disease",
    "AKI": "acute kidney injury",
    "dialysis": "dialysis care",
    "transplant": "kidney or solid-organ transplantation",
    "glomerular": "glomerular disease",
    "proteinuria": "proteinuric kidney disease",
    "ESRD": "end-stage kidney disease",
    "IgA nephropathy": "IgA nephropathy",
    "hemodialysis": "hemodialysis",
    "peritoneal dialysis": "peritoneal dialysis",
    "nephrotic syndrome": "nephrotic syndrome",
}

NEPHROLOGY_KEYWORD_RE = re.compile(
    "|".join(rf"\b{re.escape(keyword)}\b" for keyword in NEPHROLOGY_KEYWORDS),
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a daily nephrology paper digest.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch feeds and show what would be included without writing or uploading the digest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()
    dry_run = args.dry_run or settings.dry_run
    state = ProcessingState(settings.state_file)

    drive_service = None
    if not dry_run:
        if settings.skip_google_drive:
            print("Google Drive upload disabled because SKIP_GOOGLE_DRIVE=true.")
        elif not settings.google_drive_folder_id:
            raise RuntimeError(
                "Set GOOGLE_DRIVE_FOLDER_ID for uploads, or set SKIP_GOOGLE_DRIVE=true for local-only runs."
            )
        else:
            from nephro_digest.drive import build_drive_service

            drive_service = build_drive_service()

    all_papers = fetch_papers(settings.feeds)
    recent_articles = [
        paper for paper in all_papers if should_consider_paper(paper, settings.lookback_days)
    ]
    matching_articles = [
        DigestArticle(
            paper=paper,
            article_id=article_id_for_paper(paper),
            matched_keywords=matches,
            why_this_may_matter=why_this_may_matter(matches),
        )
        for paper in recent_articles
        if (matches := matched_nephrology_keywords(paper))
    ]
    unseen_articles = []
    already_seen_skipped = 0
    for article in matching_articles:
        if state.seen(article.article_id):
            already_seen_skipped += 1
        else:
            unseen_articles.append(article)

    new_articles = [
        article
        for article in unseen_articles
    ][: settings.max_articles_per_run]

    print(f"Total feed entries: {len(all_papers)}")
    print(f"Recent articles: {len(recent_articles)}")
    print(f"Nephrology matches: {len(matching_articles)}")
    print(f"Already seen skipped: {already_seen_skipped}")
    print(f"New selected: {len(new_articles)}")

    for article in new_articles:
        action = "Would include" if dry_run else "Including"
        print(f"{action}: {article.paper.journal} | {article.paper.title}")

    if dry_run:
        if not new_articles:
            print("Dry run complete. Would create a no-new-articles digest.")
        else:
            print(f"Dry run complete. Would include {len(new_articles)} articles.")
        return 0

    run_date = datetime.now(timezone.utc)
    path = write_daily_digest(settings.output_dir, new_articles, run_date)
    print(f"Wrote daily digest: {path}")
    state.mark_many([article.article_id for article in new_articles], run_date)

    digest_filename = filename_for_digest(run_date)
    if drive_service and settings.google_drive_folder_id:
        from nephro_digest.drive import file_exists, upload_markdown

        if file_exists(drive_service, settings.google_drive_folder_id, digest_filename):
            print(f"Skipping upload because {digest_filename} already exists in Google Drive.")
        else:
            uploaded_url = upload_markdown(drive_service, settings.google_drive_folder_id, path)
            print(f"Uploaded daily digest to Google Drive: {uploaded_url}")
    elif settings.skip_google_drive:
        print("Google Drive upload skipped for local-only run.")

    print(f"Processed {len(new_articles)} new articles.")
    return 0


def should_consider_paper(paper: Paper, lookback_days: int | None) -> bool:
    if paper.title.strip().lower() in NON_ARTICLE_TITLES:
        return False
    if lookback_days is None or paper.published is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return paper.published >= cutoff


def matched_nephrology_keywords(paper: Paper) -> tuple[str, ...]:
    searchable_text = f"{paper.title}\n{paper.abstract}"
    matches = {
        match.group(0).lower(): canonical_keyword(match.group(0))
        for match in NEPHROLOGY_KEYWORD_RE.finditer(searchable_text)
    }
    return tuple(sorted(matches.values(), key=lambda keyword: NEPHROLOGY_KEYWORDS.index(keyword)))


def is_nephrology_related(paper: Paper) -> bool:
    return bool(matched_nephrology_keywords(paper))


def canonical_keyword(value: str) -> str:
    normalized = value.lower()
    for keyword in NEPHROLOGY_KEYWORDS:
        if keyword.lower() == normalized:
            return keyword
    return value


def why_this_may_matter(matched_keywords: tuple[str, ...]) -> str:
    topics = []
    for keyword in matched_keywords:
        topic = KEYWORD_NOTE_TOPICS[keyword]
        if topic not in topics:
            topics.append(topic)

    if not topics:
        return "No nephrology keyword match was found."

    return (
        "The title or abstract matches nephrology keywords "
        f"({', '.join(matched_keywords)}), pointing to {format_topic_list(topics)}."
    )


def format_topic_list(topics: list[str]) -> str:
    if len(topics) == 1:
        return topics[0]
    if len(topics) == 2:
        return f"{topics[0]} and {topics[1]}"
    return f"{', '.join(topics[:-1])}, and {topics[-1]}"


if __name__ == "__main__":
    sys.exit(main())
