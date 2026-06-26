# СборкаV3

Mobile-first web app for warehouse assembly data entry. Workers scan barcodes and log box packing records directly into Google Sheets. An admin panel controls which spreadsheet tabs are visible in the app.

**Live:** deployed on Render.com (auto-deploys from `main`).

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your values
python app.py          # http://localhost:5000
```

## Environment variables

| Variable | Description |
|---|---|
| `SPREADSHEET_ID` | Google Sheets ID from the URL (`/spreadsheets/d/<ID>/edit`) |
| `SHEETS_API_KEY` | Google API key — read-only, no OAuth required |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Web client ID — used by the admin page in-browser sign-in |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full service account JSON — used server-side for all write operations |

> The `.env.example` file has `EXPO_PUBLIC_` prefixes (legacy from a prior React Native version); the app reads without that prefix.

## Google Cloud setup

1. Enable the **Google Sheets API** in your project.
2. Create an **API key** (restrict to Sheets API) → `SHEETS_API_KEY`.
3. Create an **OAuth 2.0 Web client** → `GOOGLE_CLIENT_ID`. Add your Render URL to *Authorized JavaScript origins*.
4. Create a **Service Account**, download its JSON key → `GOOGLE_SERVICE_ACCOUNT_JSON`. Share the spreadsheet with the service account email (Editor access).

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Architecture

- **`app.py`** — single-file Flask backend. All routes and Google Sheets calls live here.
- **`templates/`** — two Jinja2 templates with all JS and CSS inline (no build step).
- **`sheets_config.json`** — runtime file (gitignored) tracking which sheet tabs are active/hidden.

**Auth split:** row CRUD (add/edit/delete) uses the server-side service account — the browser never sends a token. Sheet management (add/rename/hide) in the admin panel requires the user to sign in via Google and forwards their OAuth token to the server.

## Deployment

Render reads `render.yaml`. Set environment variables in the Render dashboard (they are marked `sync: false` — not stored in this repo).
