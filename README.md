# SALA Standardized Feasibility Study for Solar AGL

This app has two supported run modes:

1. Local development / backup mode
2. Online production mode on Render

The same codebase is used for both modes. The difference is only in environment variables and service URLs.

## Architecture

- Streamlit app: UI, simulation, login, admin, archive views
- PDF service: Playwright + Chromium renderer for report export
- Postgres: users, studies, archived PDF bytes

## Local run

### 1. Install dependencies

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Prepare secrets

Copy:

- `.streamlit/secrets.example.toml` -> `.streamlit/secrets.toml`

And fill in real values.

### 3. Set env vars

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DB_NAME'
export MAPBOX_STATIC_MAPS_TOKEN='YOUR_MAPBOX_TOKEN'
export PDF_SERVICE_URL='http://127.0.0.1:8765/render'
```

### 4. Start PDF service

```bash
.venv/bin/python report/pdf_service.py
```

### 5. Start Streamlit

```bash
.venv/bin/streamlit run app.py --server.headless true --server.port 8502 --server.fileWatcherType none --browser.gatherUsageStats false
```

## Render deployment

Render setup requires three resources:

1. `sala-streamlit-app` - public Streamlit web service
2. `sala-pdf-service` - private PDF render service
3. `sala-postgres` - Render Postgres database

The `render.yaml` file in this repo describes the target layout.

### Required env vars for Streamlit service

- `DATABASE_URL`
- `MAPBOX_STATIC_MAPS_TOKEN`
- `AUTH_PERSIST_SECRET`
- `PDF_SERVICE_URL`

`PDF_SERVICE_URL` should point to the internal Render address of the private PDF service.

### Notes

- Archived PDFs are stored in Postgres.
- New PDFs are generated through the PDF service.
- The local working setup remains valid because `PDF_SERVICE_URL` still defaults to `http://127.0.0.1:8765/render`.

## Safe workflow

- Keep your current local working copy as backup.
- Use this online-prep copy for deployment work.
- Push only this prepared version to GitHub once you are happy with it.

