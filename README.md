# MachineSearch

Aggregated search platform for industrial machine listings scraped from
multiple online marketplaces.

## Repository layout

```
machinesearch/
├── backend/          # FastAPI + SQLAlchemy async Python backend
│   ├── api/          # HTTP routes (FastAPI routers)
│   ├── scraper/      # Crawling, parsing, anti-blocking
│   ├── scheduler/    # APScheduler-based periodic job runner
│   ├── database/     # SQLAlchemy models & session factory
│   ├── site_configs/ # Per-site JSON scraping configs
│   └── logs/         # Runtime log files (git-ignored except .gitkeep)
└── frontend/         # React + TypeScript SPA (to be scaffolded)
```

## Quick start (backend)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in your values
uvicorn api.main:app --reload --port 8000
```

API docs are served at `http://localhost:8000/docs` (Swagger UI).

## Environment variables

See [backend/.env.example](backend/.env.example) for the full list.

## Site configurations

Each source site is described by a JSON file in `backend/site_configs/`.
See [backend/site_configs/vib_kg.json](backend/site_configs/vib_kg.json)
for the reference schema.

## Roadmap

- [ ] Implement scraper CSS selectors for all target sites
- [ ] Implement full-text search (PostgreSQL FTS or Elasticsearch)
- [ ] Add Alembic migrations
- [ ] Scaffold and build the React frontend
- [ ] Containerise with Docker Compose (API + DB + Redis)
- [ ] Add CI/CD pipeline (GitHub Actions)
- [ ] Write integration test suite
