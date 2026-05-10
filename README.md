# Daily Nephrology Paper Digest

This project checks RSS feeds for Kidney International, CJASN, JASN, NEJM, Transplantation, and the American Journal of Transplantation. It extracts each paper's title, abstract or feed summary, DOI, and URL, generates a concise nephrology-focused summary with the OpenAI API, saves a Markdown file, and uploads it to a Google Drive folder.

## Project Layout

- `nephro_digest/config.py` - feed URLs and environment-based settings
- `nephro_digest/feeds.py` - RSS parsing, DOI extraction, and article normalization
- `nephro_digest/summarizer.py` - OpenAI summary generation
- `nephro_digest/markdown.py` - Markdown rendering and deterministic filenames
- `nephro_digest/drive.py` - Google Drive authentication and uploads
- `nephro_digest/state.py` - duplicate-processing state
- `.github/workflows/daily.yml` - daily GitHub Actions automation

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set required environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_DRIVE_FOLDER_ID="your-drive-folder-id"
export GOOGLE_SERVICE_ACCOUNT_INFO='{"type":"service_account", ...}'
```

You can use `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json` instead of `GOOGLE_SERVICE_ACCOUNT_INFO` for local runs.

Run a dry check without calling OpenAI or Google Drive:

```bash
python -m nephro_digest.main --dry-run
```

Run the full digest:

```bash
python -m nephro_digest.main
```

## GitHub Actions Secrets

In your GitHub repository, add these secrets:

- `OPENAI_API_KEY`
- `GOOGLE_SERVICE_ACCOUNT_INFO`
- `GOOGLE_DRIVE_FOLDER_ID`

Optional repository variables:

- `OPENAI_MODEL` - defaults to `gpt-5.2`
- `MAX_PAPERS_PER_RUN` - defaults to `50`
- `LOOKBACK_DAYS` - defaults to `14`; set to `0` to process all feed entries not already seen
- `SKIP_GOOGLE_DRIVE` - set to `true` only for local-only testing

The workflow runs every day at `12:00 UTC`, which is morning in US time zones for much of the year. Edit the cron entry in `.github/workflows/daily.yml` if you want a different local morning.

## Google Drive Setup

1. Create a Google Cloud project.
2. Enable the Google Drive API.
3. Create a service account and download its JSON key.
4. Share the target Google Drive folder with the service account email address.
5. Store the full JSON key as the `GOOGLE_SERVICE_ACCOUNT_INFO` GitHub secret.

The app uses the `drive.file` OAuth scope and uploads Markdown files into the configured folder.

## Duplicate Avoidance

The digest avoids duplicate work in two ways:

- It stores stable article IDs in `.state/processed.json`.
- It checks Google Drive for an existing deterministic Markdown filename before generating a new summary.

GitHub Actions restores and saves `.state` with the Actions cache. The Drive filename check is a second layer in case the cache is missing.

By default, the script only considers feed entries published in the last 14 days, which prevents first runs from processing stale back catalogs exposed by some publisher feeds.

## RSS Feeds

Default feeds are defined in `nephro_digest/config.py`. You can override them with `FEED_URLS_JSON`:

```bash
export FEED_URLS_JSON='{
  "KI": ["https://www.kidney-international.org/current.rss"],
  "NEJM": ["https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss"]
}'
```

Some publisher feeds, especially LWW-hosted feeds, may apply bot protection. If a publisher changes or blocks an RSS endpoint, update `FEED_URLS_JSON` or the defaults in `nephro_digest/config.py`.

## Output

Markdown files are written under `summaries/YYYY-MM-DD/` and uploaded to Google Drive. Each file contains:

- Title
- Journal
- Publication date
- DOI
- URL
- Nephrology-focused summary
- Abstract or feed summary
