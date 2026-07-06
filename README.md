# 🤝 Personalized Networking Assistant

> AI-powered conversation starters and Wikipedia fact-checking for professional networking events.

**SkillWallet · Google Cloud Generative AI Module**

---

## Overview

The Personalized Networking Assistant helps professionals walk into any networking event
ready to start meaningful conversations. It uses:

| Component | Technology |
|-----------|-----------|
| **Theme Extraction** | DistilBERT zero-shot classification (HuggingFace) |
| **Starter Generation** | Google Gemini 2.5 Flash (with GPT-2 Small fallback) |
| **Fact Verification** | Wikipedia API |
| **Backend API** | FastAPI + SQLAlchemy + SQLite |
| **Frontend UI** | Streamlit + Linear Orbit Design System |

---

## Features

- ✨ **Generate Starters** — Enter your bio and event description → get 1–5 personalised conversation openers
- 🔍 **Fact Check** — Verify any topic on Wikipedia with a trimmed summary and source link
- 📜 **History** — Browse all past sessions with themes, starters, and context
- 💬 **Feedback** — Rate starters with 👍/👎 to track model quality
- 🔗 **Demo & GitHub links** — Sidebar fields for mentor review
- 📖 **OpenAPI docs** — Auto-generated at `http://localhost:8000/docs`

---

## Prerequisites

- Python **3.10+**
- Git
- ~3 GB disk space (for HuggingFace model cache on first run)
- Internet connection (for Gemini API and Wikipedia lookups)
- A Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com/app/apikey))

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/personalized-networking-assistant.git
cd personalized-networking-assistant
```

### 2. Create a virtual environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `torch` is included in `requirements.txt`. If you want a smaller,
> CPU-only install, replace the torch line with:
> ```
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> ```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your Gemini API key:

```env
GEMINI_API_KEY="your-gemini-api-key-here"
USE_GEMINI=true
```

### 5. Start the backend API

```bash
# From the project root
uvicorn backend.main:app --reload --port 8000
```

You should see:

```
INFO: Starting Personalized Networking Assistant v1.0.0
INFO: Database tables ready.
INFO: DistilBERT zero-shot classifier warmed up.
INFO: Startup complete. API is ready.
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 6. Start the frontend (new terminal)

```bash
# Activate your venv first, then:
streamlit run frontend/app.py --server.port 8501
```

### 7. Open the application

| URL | Description |
|-----|-------------|
| `http://localhost:8501` | Streamlit frontend |
| `http://localhost:8000/docs` | FastAPI OpenAPI docs |
| `http://localhost:8000/redoc` | ReDoc documentation |
| `http://localhost:8000/health` | Health check JSON |

---

## Using the Makefile

If you have `make` installed (Linux/macOS or Windows with Git Bash):

```bash
make install      # Install dependencies
make dev-api      # Start FastAPI backend
make dev-ui       # Start Streamlit frontend
make test         # Run all pytest tests
make test-watch   # Run tests in watch mode
make clean        # Remove .db, __pycache__, .pyc files
```

---

## Project Structure

```
personalized-networking-assistant/
├── backend/
│   ├── main.py              # FastAPI app factory + lifespan
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # SQLAlchemy engine + get_db()
│   ├── models/              # SQLAlchemy ORM models (6 tables)
│   ├── schemas/             # Pydantic v2 request/response schemas
│   ├── routers/             # FastAPI APIRouters (no business logic)
│   ├── services/            # Business logic + AI services
│   └── tests/               # pytest unit + integration tests
├── frontend/
│   ├── app.py               # Streamlit entry point
│   ├── config.py            # Frontend config + helpers
│   ├── pages/               # Tab renderers (one per tab)
│   ├── components/          # Reusable card/table components
│   └── styles/
│       └── linear_orbit.css # Design system (from DESIGN.md)
├── .env.example             # Environment template
├── requirements.txt         # All Python dependencies
├── README.md                # This file
└── Makefile                 # Development shortcuts
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/generate` | Generate conversation starters |
| `GET` | `/api/v1/fact-check?query=…` | Wikipedia fact-check |
| `GET` | `/api/v1/history` | Session history (paginated) |
| `POST` | `/api/v1/feedback` | Submit thumbs-up/down |
| `GET` | `/api/v1/feedback-history` | All feedback entries |
| `GET` | `/health` | API health check |

Full interactive documentation is available at `http://localhost:8000/docs`.

---

## Running Tests

```bash
# From the project root with venv active:
pytest backend/tests/ -v

# Run a specific test module:
pytest backend/tests/test_api_routes.py -v

# With coverage (if pytest-cov is installed):
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

All tests mock the AI model pipeline and Wikipedia client, so no API key or
internet connection is required to run the test suite.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | **Required.** Google Gemini API key |
| `USE_GEMINI` | `true` | Use Gemini (true) or local GPT-2 (false) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `DATABASE_URL` | SQLite file | SQLAlchemy connection URL |
| `ZERO_SHOT_MODEL` | DistilBERT | HuggingFace zero-shot model |
| `MAX_THEMES` | `5` | Max themes extracted per event |
| `BACKEND_PORT` | `8000` | FastAPI port |
| `CORS_ORIGINS` | `localhost:8501` | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Design System

The UI follows the **Linear Orbit** design system (see `DESIGN.md`):

- **Fonts:** Inter Display, Inter, JetBrains Mono
- **Accent:** Indigo `#5e6ad2`
- **Surface:** Pure white `#ffffff` on `#f5f6f8` page background
- **Dividers:** 6% ink `rgba(14,17,22,0.06)`
- **Radius:** 5px (sm) · 8px (md) · 10px (lg)

---

## Demo & Repository

| | Link |
|--|------|
| 🔗 **Live Demo** | _Add demo URL here_ |
| 📦 **GitHub** | _Add GitHub URL here_ |

---

## Team

**Team Lead:** Bhaumik Hinunia  
**Module:** Google Cloud Generative AI — SkillWallet Group Project  
**Platform:** [myskillwallet.ai](https://myskillwallet.ai)
