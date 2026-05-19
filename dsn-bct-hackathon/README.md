# DSN BCT Hackathon

Project scaffold for the DSN BCT Hackathon.

Structure:

- app/: FastAPI application and client wrappers
- data/: sample data for testing
- .env: environment variables (keep secrets out of git)
- requirements.txt: Python dependencies
- docker-compose.yml: starts the API on port 8000

Quick start:

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Run the app:

```bash
uvicorn app.main:app --reload
```
