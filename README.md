# СборкаV3

Mobile-first web app for warehouse assembly data entry. Workers scan barcodes and log box packing records into a PostgreSQL database. An admin panel controls which data sections are visible. Any section can be exported to Excel.

**Live:** deployed on Render.com (auto-deploys from `main`).

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL
python app.py          # http://localhost:5000
```

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |

Tables are created automatically on first run.

## Database setup

You can use any PostgreSQL provider:

- **Render** — add a PostgreSQL database in the Render dashboard, use the *Internal Database URL* as `DATABASE_URL`
- **Neon** — free tier at neon.tech, copy the connection string
- **Supabase** — free tier at supabase.com, use the *URI* from project settings → Database

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Architecture

- **`app.py`** — single-file Flask backend. PostgreSQL via psycopg2. All routes live here.
- **`templates/`** — two Jinja2 templates with all JS and CSS inline (no build step).
  - `index.html` — worker UI with barcode scanner and Excel export
  - `admin.html` — sheet management (add, rename, hide, restore)

## Deployment

Render reads `render.yaml`. Set `DATABASE_URL` in the Render dashboard (marked `sync: false` — not stored in this repo).
