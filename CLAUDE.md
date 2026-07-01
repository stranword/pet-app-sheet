# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A mobile-first Flask web app ("СборкаV3") for managing warehouse assembly data. Workers scan barcodes and record box packing data; a separate admin page manages which data sections (sheets) are visible. Data is stored in PostgreSQL; users can export any sheet to Excel (.xlsx).

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

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Environment Variables

Required in `.env` (see `.env.example`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (e.g. from Render, Neon, Supabase) |

## Architecture

### Backend (`app.py`)

Single-file Flask app. All logic lives here — no blueprints or separate modules.

**Database helpers:**
- `get_db()` — opens a psycopg2 connection using `DATABASE_URL`
- `db_execute(sql, params, fetch)` — runs a single statement, commits, returns rows if `fetch='all'`/`'one'`
- `db_transaction(queries)` — runs multiple statements in one transaction
- `init_db()` — creates `sheets` and `rows` tables if they don't exist; inserts default sheets

**Sheet config:** Stored in the `sheets` DB table (`name TEXT PRIMARY KEY, status TEXT`). `load_config()` reads active/deleted sheets from there. Default sheets on first run: `['Ратчин', 'ЧСА', 'ЕОГ', 'ДАА']`. "Deleting" a sheet in admin only marks it as `status='deleted'` — row data is preserved.

**No authentication** — all endpoints are open. Suitable for an internal LAN/VPN deployment.

### DB Schema

**`sheets`**
| Column | Type | Notes |
|---|---|---|
| `name` | TEXT PK | Sheet name |
| `status` | TEXT | `'active'` or `'deleted'` |

**`rows`**
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | Auto-increment |
| `sheet_name` | TEXT | Matches `sheets.name` |
| `shk` | TEXT | Barcode (штрихкод) |
| `kolichestvo` | TEXT | Quantity |
| `nomer_koroba` | TEXT | Box number |
| `data` | TEXT | Datetime, format `DD.MM.YYYY HH:MM` |

### API

| Method | Path | Description |
|---|---|---|
| GET | `/api/rows/<sheet>` | List rows for a sheet |
| POST | `/api/rows/<sheet>` | Add a row |
| PUT | `/api/rows/<sheet>/<id>` | Update a row by id |
| DELETE | `/api/rows/<sheet>/<id>` | Delete a row by id |
| GET | `/api/export/<sheet>` | Download sheet as .xlsx |
| GET | `/api/admin/sheets` | Get active/deleted config |
| POST | `/api/admin/sheets` | Add a new sheet |
| PUT | `/api/admin/sheets/rename` | Rename a sheet |
| POST | `/api/admin/sheets/delete` | Soft-delete a sheet |
| POST | `/api/admin/sheets/restore` | Restore a deleted sheet |

### Frontend (`templates/`)

Vanilla JS + inline CSS, no build step.

- `index.html`: Main worker UI. Tabs per active sheet, barcode scanner (`html5-qrcode@2.3.8`, supports QR and 1D barcodes), add/edit/delete rows via a bottom-sheet modal, filter by barcode or date, 📥 Excel export button.
- `admin.html`: Sheet management. No auth required — add, rename, soft-delete, restore sheets.

### Legacy TypeScript Files (`lib/`)

`lib/sheets.ts` and `lib/auth.ts` are from a previous React Native/Expo implementation and are **not used** by the Flask app.

## Deployment

Deployed on Render.com via `render.yaml`. Build: `pip install -r requirements.txt`. Start: `gunicorn app:app`. Set `DATABASE_URL` in the Render dashboard. Render also offers a managed PostgreSQL add-on (`render.com/docs/databases`).
