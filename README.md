# AI Email Agent

A Python starter project for an autonomous email assistant that:
- Reads unread Gmail messages
- Classifies email intent (`meeting`, `query`, `spam`, `info`, `attachment`)
- Decides a safe action using confidence thresholds
- Executes actions (draft reply, archive, save attachments, calendar event)

## Safety defaults
- Dry-run is enabled by default.
- Auto-send is not implemented; replies are created as drafts.
- Low-confidence decisions are marked as `needs_review`.

## Stack
- Python 3.10+
- Gmail API + Google Calendar API
- OpenAI API (optional, heuristic fallback if no API key)

## Project layout

```text
ai-email-agent/
  app/
    actions.py
    classifier.py
    decision_engine.py
    gmail_client.py
    main.py
    models.py
    prompts.py
  data/
  tests/
  requirements.txt
  .env.example
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure Google Cloud:
- Enable Gmail API and Google Calendar API.
- Create OAuth desktop credentials and download `credentials.json`.
- Place `credentials.json` in the project root (or set `GMAIL_CREDENTIALS_FILE`).

4. Create environment file:

```bash
cp .env.example .env
```

5. Edit `.env` with your keys/settings.

## Run

Dry-run (safe, no changes):

```bash
python -m app.main --max-emails 10
```

Execute actions:

```bash
python -m app.main --execute --max-emails 10 --save-attachments-dir ./data/attachments
```

## What happens on first run
Google OAuth opens a consent flow and creates `token.json`.

## CI/CD

GitHub Actions workflow: `.github/workflows/ci-cd.yml`

- Pull requests run the test suite and verify that the Docker image builds.
- Pushes to `main` run the same checks, publish an image to GitHub Container
  Registry, then deploy it through SSH to the configured production server.

Configure these GitHub repository secrets before enabling production deployment:

- `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, and optional `DEPLOY_PORT`
- `DEPLOY_PATH`: directory on the server containing the deployment
  `compose.yaml` and its protected runtime credentials.

The server compose file should reference `${IMAGE}` for its service image. OAuth
credentials, `token.json`, and `.env` stay on the server and are excluded from
the image.

## Notes
- Meeting event creation needs extracted `start_iso` and `end_iso` from classifier output.
- If time extraction is missing, the agent falls back to a review-safe action.
