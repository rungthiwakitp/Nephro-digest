# Daily Nephrology Paper Digest

This project checks RSS feeds for Kidney International, CJASN, JASN, NEJM, Transplantation, and the American Journal of Transplantation. It extracts article metadata, filters for nephrology-relevant articles using title and abstract keywords, generates a deterministic Markdown digest, and uploads the digest to Google Drive.

No OpenAI API key or paid AI service is required.

## Project Layout

- `nephro_digest/config.py` - feed URLs and environment-based settings
- `nephro_digest/feeds.py` - RSS parsing, DOI extraction, and article normalization
- `nephro_digest/main.py` - filtering, digest generation, and upload orchestration
- `nephro_digest/markdown.py` - daily Markdown digest rendering
- `nephro_digest/drive.py` - Google Drive authentication and upload
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
export GOOGLE_DRIVE_FOLDER_ID="your-drive-folder-id"
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account", ...}'
```

You can use `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json` instead of `GOOGLE_SERVICE_ACCOUNT_JSON` for local runs.

Run a dry check without writing or uploading a digest:

```bash
python -m nephro_digest.main --dry-run
```

Run the full digest:

```bash
python -m nephro_digest.main
```

## GitHub Actions Secrets

In your GitHub repository, add these secrets:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_DRIVE_FOLDER_ID`

Optional repository variables:

- `MAX_ARTICLES_PER_RUN` - defaults to `10`
- `LOOKBACK_DAYS` - defaults to `14`; set to `0` to process all feed entries not already seen
- `SKIP_GOOGLE_DRIVE` - set to `true` only for local-only testing

The workflow runs every day at `12:00 UTC`. Edit the cron entry in `.github/workflows/daily.yml` if you want a different morning time.

## Google Drive Setup

1. Create a Google Cloud project.
2. Enable the Google Drive API.
3. Create a service account and download its JSON key.
4. Share the target Google Drive folder with the service account email address.
5. Store the full JSON key as the `GOOGLE_SERVICE_ACCOUNT_JSON` GitHub secret.

The app uses the `drive.file` OAuth scope and uploads Markdown files into the configured folder.

## Filtering

The script only includes articles whose title or abstract contains one or more nephrology keywords:

- `kidney`
- `renal`
- `nephrology`
- `CKD`
- `AKI`
- `dialysis`
- `transplant`
- `glomerular`
- `proteinuria`
- `ESRD`
- `IgA nephropathy`
- `hemodialysis`
- `peritoneal dialysis`
- `nephrotic syndrome`

The "Why this may matter" note is generated only from matched keywords. It does not summarize, infer, or use AI.

By default, the script only considers feed entries published in the last 14 days, which prevents first runs from processing stale back catalogs exposed by some publisher feeds.

## Duplicate Avoidance

The digest stores stable article IDs in `.state/processed.json` after a digest is written and uploaded or intentionally run in local-only mode. GitHub Actions restores and saves `.state` with the Actions cache.

The upload step also checks Google Drive for an existing daily digest filename before uploading another file with the same name.

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

One Markdown digest is written under `summaries/YYYY-MM-DD/` and uploaded to Google Drive. Each included article contains:

- Journal
- Title
- Publication date
- DOI
- URL
- Abstract
- Matched keywords
- "Why this may matter" note based only on keyword matches
