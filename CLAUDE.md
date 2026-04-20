# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wetsu Finance is a personal finance management app for tracking income, expenses, investments, and transfers. It is built for Chilean peso (CLP) and includes bilingual content (Spanish/English). There is also a financial analysis agent called **Donatello** (`agents/donatello/`) that queries the database and generates reports.

## Development Commands

```bash
# Install dependencies
cd app && pip install -r requirements.txt

# Run development server (auto-reload)
cd app && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run production server
python app/main.py

# Initialize or reinitialize the database from a CSV export
python scripts/init_db.py

# Reclassify "Miscelánea" transactions using keyword rules
python scripts/refine_misc.py

# Run the Donatello finance agent directly
python agents/donatello/donatello.py
```

There is no test suite and no CI/CD pipeline configured.

## Architecture

### Stack

- **Backend**: FastAPI + SQLite (no ORM, raw `sqlite3` with parameterized queries)
- **Frontend**: Vanilla HTML/CSS/JS + Chart.js (no build step, no bundler)
- **Server**: Uvicorn + Systemd (production on VPS)
- **Agent**: Python class-based CLI agent (`agents/donatello/`)

### Hardcoded Paths

`app/main.py` and `scripts/init_db.py` have **hardcoded absolute paths** for the database and static/template directories pointing to `/root/.openclaw/workspace/finance/`. The Donatello agent defaults to `/opt/wetsu-finance/data/finance.db`. When running locally or deploying to a different path, update these constants at the top of each file.

### API Layer (`app/main.py`)

All business logic lives in a single file. The FastAPI app:
- Mounts `/static` directly from the filesystem (no compilation)
- Serves `index.html` via file read on every `GET /`
- Exposes seven REST endpoints under `/api/`
- Builds dynamic SQL strings by appending `AND` clauses and `?` params — this pattern is used throughout; extend it consistently

Key Pydantic models:
- `Transaction` — full model for creation (`source` defaults to `"app"`, `currency` defaults to `"CLP"`)
- `TransactionUpdate` — all fields optional, used for partial PATCH-style PUT

### Database (`data/schema.sql`, `data/finance.db`)

Four tables: `transactions`, `categories`, `budgets`, `savings_goals`. Only `transactions` and `categories` are actively used by the app. `budgets` and `savings_goals` exist in the schema but have no API endpoints yet.

**Key conventions:**
- `amount` is stored as a plain integer (CLP has no decimal subdivisions — no cents multiplication needed)
- `date` is stored as `TEXT` in `YYYY-MM-DD` format
- `type` is constrained to: `income`, `expense`, `transfer`, `investment`
- `category_main` / `category_sub` are free-text strings matched against the `categories` table (no FK constraint enforced)
- `source` tracks data origin: `buddy` (imported from Buddy app CSV), `manual`, `bank`, `app`

### Frontend (`app/static/app.js`, `app/templates/index.html`)

Single-page app with three tabs: Dashboard, Transactions, Add New. Global state is minimal (`currentPage`, `pageSize`, `categories`). The JS fetches `/api/categories` on load and caches it to populate form dropdowns.

Charts use Chart.js (loaded from CDN): a doughnut for expense categories and a bar chart for monthly income vs. expense trends.

Amounts are always formatted as Chilean pesos using `Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' })`.

### Donatello Agent (`agents/donatello/`)

A standalone Python class that connects directly to the SQLite database (bypassing the API) and generates financial summaries, alerts, and weekly/monthly reports. Refer to `AGENT.md` for command vocabulary and `IDENTITY.md` for personality and scope boundaries. The agent communicates in Spanish and uses emoji status indicators (🟢/🟡/🔴).

## Key Conventions

- **Currency**: All amounts are CLP integers. Never introduce float arithmetic for money.
- **Language**: Category names, schema comments, and agent interactions are in Spanish. Code identifiers and API field names are in English.
- **DB access**: Always open and close connections per-request (`get_db()` + `conn.close()`). No connection pooling.
- **Categories**: When adding new category entries, insert them into the `categories` table via `schema.sql` or directly in the DB — the API reads them dynamically.
- **Production deploy**: `git pull` on the VPS then `sudo systemctl restart wetsu-finance`.
