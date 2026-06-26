# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A mobile-first Flask web app ("СборкаV3") for managing warehouse assembly data in Google Sheets. Workers scan barcodes and record box packing data; a separate admin page manages which spreadsheet tabs are visible.

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Development server
python app.py

# Production (used on Render)
gunicorn app:app
```

There are no tests in this project.

## Environment Variables

Required in `.env` (see `.env.example`):

| Variable | Purpose |
|---|---|
| `SPREADSHEET_ID` | Google Sheets spreadsheet ID (from the URL) |
| `SHEETS_API_KEY` | API key for read-only public sheet access |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID for admin sheet management (browser-side) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON of a service account with editor access (for server-side writes) |

Note: `.env.example` uses `EXPO_PUBLIC_` prefixes (a leftover from the prior React Native version); `app.py` reads the variables without that prefix.

## Architecture

### Backend (`app.py`)

Single-file Flask app. All logic lives here — no blueprints or separate modules.

**Dual authentication model:**
- **Row CRUD** (`/api/rows/<sheet>` POST/PUT/DELETE): Uses the server-side service account (`GOOGLE_SERVICE_ACCOUNT_JSON`). The browser sends no auth token; the server obtains and caches a Bearer token via `google-auth`.
- **Sheet management** (`/api/admin/sheets` POST/PUT): Requires the user's Google OAuth token passed as `Authorization: Bearer <token>` from the browser. The admin page handles sign-in via the Google Identity Services (GSI) client library and stores the token in `sessionStorage`.

**Sheet config (`sheets_config.json`):**  
Tracked locally (not in git) as `{"active": [...], "deleted": [...]}`. Default sheets on first run: `['Ратчин', 'ЧСА', 'ЕОГ', 'ДАА']`. "Deleting" a sheet in admin only hides it from the app — the actual tab in Google Sheets is not removed.

### Spreadsheet Column Mapping (A–G)

| Column | Field | Notes |
|---|---|---|
| A | `shk` | Barcode (штрихкод) |
| B | *(empty)* | Reserved (tovar) |
| C | `artVB` | Wildberries article |
| D | *(empty)* | Reserved (razmer) |
| E | `kolichestvo` | Quantity |
| F | `nomerKoroba` | Box number |
| G | `data` | Datetime, format `DD.MM.YYYY HH:MM` |

### Frontend (`templates/`)

Vanilla JS + inline CSS, no build step. All JS is embedded in the HTML files.

- `index.html`: Main worker UI. Tabs per active sheet, barcode scanner (jsQR via camera), add/edit/delete rows via a bottom-sheet modal, filter by barcode or date.
- `admin.html`: Sheet management. Inline Google Sign-In flow; token held in `sessionStorage`. Sheet "delete" is soft (local config only).

### Legacy TypeScript Files (`lib/`)

`lib/sheets.ts` and `lib/auth.ts` are from a previous React Native/Expo implementation and are **not used** by the Flask app. They exist as reference. `lib/auth.ts` uses `expo-auth-session`; `lib/sheets.ts` uses `axios` against the Sheets API v4.

## Deployment

Deployed on Render.com via `render.yaml`. Build: `pip install -r requirements.txt`. Start: `gunicorn app:app`. Environment variables are set manually in the Render dashboard (`sync: false`).
