# Wetsu Finance

Personal finance management app for Wetsu.

## Stack
- **Backend**: FastAPI + SQLite
- **Frontend**: Vanilla HTML/CSS/JS + Chart.js
- **Server**: Uvicorn + Systemd

## Structure
```
app/           # FastAPI application
├── main.py    # Main API
├── static/    # CSS/JS assets
└── templates/ # HTML templates

data/          # SQLite database
└── finance.db

scripts/       # Database utilities
```

## Development

### Local Setup
```bash
cd app
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deploy
```bash
# On VPS
cd /opt/wetsu-finance
git pull
sudo systemctl restart wetsu-finance
```

## Database
SQLite database stored in `data/finance.db`.

## Author
Wetsu (Jesus Morillo)
