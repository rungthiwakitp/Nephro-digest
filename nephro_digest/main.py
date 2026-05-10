from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from nephro_digest.config import load_settings
from nephro_digest.feeds import Paper, fetch_papers
from nephro_digest.markdown import filename_for_paper, render_markdown, write_summary
from nephro_digest.state import ProcessingState
from nephro_digest.summarizer import summarize_paper


NON_ARTICLE_TITLES = {
    "table of contents",
    "subscription information",
    "editorial board",
    "outside front cover",
    "inside front cover",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a daily nephrology paper digest.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch feeds and show what would be processed without calling OpenAI or Google Drive.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()
    dry_run = args.dry_run or settings.dry_run
    state = ProcessingState(settings.state_file)

    drive_service = None
    if not dry_run:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY before running the full digest.")
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
    papers = [paper for paper in all_papers if should_consider_paper(paper, settings.lookback_days)]
    print(
        f"Found {len(all_papers)} feed entries across {len(settings.feeds)} journal feeds; "
        f"{len(papers)} are eligible for this run."
    )

    processed_this_run = 0
    for paper in papers:
        if processed_this_run >= settings.max_papers_per_run:
            print(f"Reached MAX_PAPERS_PER_RUN={settings.max_papers_per_run}; stopping.")
            break

        filename = filename_for_paper(paper)
        if state.seen(paper.stable_id):
            continue

        if drive_service and settings.google_drive_folder_id:
            from nephro_digest.drive import file_exists

        if drive_service and settings.google_drive_folder_id and file_exists(
            drive_service, settings.google_drive_folder_id, filename
        ):
            print(f"Skipping already-uploaded file: {filename}")
            state.mark(paper.stable_id)
            continue

        action = "Would process" if dry_run else "Processing"
        print(f"{action}: {paper.journal} | {paper.title}")
        if dry_run:
            processed_this_run += 1
            continue

        summary = summarize_paper(
            paper,
            model=settings.openai_model,
            max_output_tokens=settings.max_output_tokens,
        )
        markdown = render_markdown(paper, summary)
        path = write_summary(settings.output_dir, paper, markdown)
        print(f"Wrote {path}")

        if drive_service and settings.google_drive_folder_id:
            from nephro_digest.drive import upload_markdown

            uploaded_url = upload_markdown(drive_service, settings.google_drive_folder_id, path)
            print(f"Uploaded to Google Drive: {uploaded_url}")
        elif settings.skip_google_drive:
            print("Google Drive upload skipped for local-only run.")

        state.mark(paper.stable_id)
        processed_this_run += 1

    if dry_run:
        print(f"Dry run complete. Would process {processed_this_run} new papers.")
    elif processed_this_run == 0:
        print("No new papers to summarize.")
    else:
        print(f"Processed {processed_this_run} new papers.")

    return 0


def should_consider_paper(paper: Paper, lookback_days: int | None) -> bool:
    if paper.title.strip().lower() in NON_ARTICLE_TITLES:
        return False
    if lookback_days is None or paper.published is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return paper.published >= cutoff


if __name__ == "__main__":
    sys.exit(main())
