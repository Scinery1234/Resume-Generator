# Resume Generator

A full-stack web application that uses AI (OpenAI GPT) to generate professionally tailored, Australian-style resumes. Upload your existing documents, paste a job description, and receive a polished `.docx` resume and live HTML preview.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Clone the repository](#1-clone-the-repository)
  - [2. Set up environment variables](#2-set-up-environment-variables)
  - [3. Install backend dependencies](#3-install-backend-dependencies)
  - [4. Install frontend dependencies](#4-install-frontend-dependencies)
- [Running the Application](#running-the-application)
  - [Start the backend](#start-the-backend)
  - [Start the frontend](#start-the-frontend)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Deployment](#deployment)

---

## Features

- **AI-powered resume generation** — Upload old resumes, LinkedIn exports, or any supporting documents; the AI extracts and tailors your experience to a specific job description.
- **Additional information support** — Include selection criteria responses, key achievements, or any extra context that the AI will weave throughout the resume.
- **Australian resume conventions** — Follows current standards: professional summary, no DOB/photo, "Month Year" date format, ATS optimisation.
- **Dual output formats** — Downloads a professionally formatted `.docx` Word document and shows a live HTML preview.
- **Resume editing** — Edit a generated resume using a natural-language prompt or direct inline editing.
- **User accounts** — Save, view, and manage your generated resumes across sessions.
- **Demo account** — A pre-seeded demo user (`demo@example.com` / `demo1234`) is available for quick exploration.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend framework | FastAPI | ≥ 0.104.0 |
| ASGI server | Uvicorn | ≥ 0.24.0 |
| Data validation | Pydantic | ≥ 2.5.0 |
| AI integration | OpenAI Python SDK | ≥ 1.3.0 |
| ORM | SQLAlchemy | ≥ 2.0.23 |
| Word document generation | python-docx | ≥ 1.1.0 |
| PDF text extraction | pypdf | ≥ 3.0.0 |
| Database (local) | SQLite | built-in |
| Database (production) | PostgreSQL | via psycopg2-binary ≥ 2.9.0 |
| Frontend framework | React | 18.x |
| Frontend routing | react-router-dom | 6.x |
| HTTP client | Axios | 1.6.x |
| CSS-in-JS | styled-components | 5.3.x |
| Node.js | — | ≥ 18.0.0 |
| npm | — | ≥ 9.0.0 |
| Python | — | ≥ 3.9 |

---

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

- **Python 3.9+** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** and **npm 9+** — [nodejs.org](https://nodejs.org/)
- **An OpenAI API key** — [platform.openai.com](https://platform.openai.com/)

Verify your installations:

```bash
python --version   # should be 3.9 or higher
node --version     # should be 18.x or higher
npm --version      # should be 9.x or higher
```

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd Resume-Generator
```

### 2. Set up environment variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and add your configuration:

```env
# Required: your OpenAI API key from https://platform.openai.com/
OPENAI_API_KEY=sk-...

# Optional: comma-separated list of allowed CORS origins (default: http://localhost:3000)
# Use "*" to allow all origins during development
CORS_ORIGINS=http://localhost:3000

# Optional: override the default OpenAI model (default: gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini

# Optional: override upload/resume directories (defaults shown)
UPLOAD_DIR=./uploads
RESUMES_DIR=./resumes

# Optional: PostgreSQL connection string for production (omit for local SQLite)
# DATABASE_URL=postgresql://user:password@host:5432/dbname
```

> **Note:** The application will start without a valid `OPENAI_API_KEY`, but resume generation will be unavailable until one is configured.

### 3. Install backend dependencies

It is recommended to use a virtual environment:

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows

# Install all Python dependencies
pip install -r requirements.txt
```

**Backend Python packages installed:**

| Package | Version | Purpose |
|---|---|---|
| fastapi | ≥ 0.104.0 | Web framework |
| uvicorn[standard] | ≥ 0.24.0 | ASGI server |
| pydantic[email] | ≥ 2.5.0 | Data validation & serialisation |
| openai | ≥ 1.3.0 | OpenAI API client |
| python-dotenv | ≥ 1.0.0 | `.env` file loading |
| sqlalchemy | ≥ 2.0.23 | ORM and database abstraction |
| python-docx | ≥ 1.1.0 | Word document generation |
| python-multipart | ≥ 0.0.6 | File upload parsing |
| psycopg2-binary | ≥ 2.9.0 | PostgreSQL driver |
| pypdf | ≥ 3.0.0 | PDF text extraction |
| pytest | ≥ 7.4.0 | Test runner |
| pytest-asyncio | ≥ 0.21.0 | Async test support |
| httpx | ≥ 0.25.0 | HTTP client for tests |

### 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### Start the backend

From the project root (with your virtual environment active):

```bash
uvicorn main:app --reload
```

The backend starts at **http://localhost:8000**.

- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Alternative API docs (ReDoc): http://localhost:8000/redoc
- Health check: http://localhost:8000/health

### Start the frontend

In a separate terminal, from the project root:

```bash
cd frontend
npm start
```

The frontend starts at **http://localhost:3000** and proxies API requests to port 8000 automatically.

---

## API Reference

All endpoints are documented interactively at http://localhost:8000/docs. Key endpoints:

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/` | Root health check |
| GET | `/health` | Detailed health status |

### Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/signup` | Register a new user |
| POST | `/api/auth/login` | Log in and receive a token |

**Signup request body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "password": "securepassword"
}
```

**Login request body:**
```json
{
  "email": "jane@example.com",
  "password": "securepassword"
}
```

### Resume Generation (Primary Flow)

| Method | Path | Description |
|---|---|---|
| POST | `/api/generate` | Generate resume from uploaded documents + job description |

This is a `multipart/form-data` request:

| Field | Type | Required | Description |
|---|---|---|---|
| `files` | File(s) | Yes | 1–5 files (`.pdf`, `.docx`, `.doc`, `.txt`, max 50 MB each) |
| `job_description` | string | Yes | The full job description text |
| `additional_info` | string | No | Selection criteria responses, key achievements, or extra context |
| `user_id` | integer | No | If provided, saves the resume to the user's account |

**Example using curl:**
```bash
curl -X POST http://localhost:8000/api/generate \
  -F "files=@my_resume.pdf" \
  -F "job_description=We are looking for a Senior Software Engineer..." \
  -F "additional_info=I led a team of 8 engineers and reduced costs by 30%." \
  -F "user_id=1"
```

**Response:**
```json
{
  "status": "success",
  "filename": "resume_abc123.docx",
  "download_url": "/api/resumes/download-file/resume_abc123.docx",
  "preview_html": "<!DOCTYPE html>...",
  "data": { ... },
  "resume_id": 42
}
```

### Resume Management

| Method | Path | Description |
|---|---|---|
| GET | `/api/resumes?user_id={id}` | List all resumes for a user |
| GET | `/api/resumes/{resume_id}/download` | Download resume `.docx` by database ID |
| GET | `/api/resumes/download-file/{filename}` | Download resume `.docx` by filename |
| DELETE | `/api/resumes/{resume_id}` | Delete a resume |
| POST | `/api/resumes/{resume_id}/edit` | Edit resume via AI prompt |
| PUT | `/api/resumes/{resume_id}/update` | Update resume data directly (inline editing) |

### User

| Method | Path | Description |
|---|---|---|
| GET | `/api/users/{user_id}/prompt-info` | Get prompt usage and membership tier |

---

## Running Tests

The project has both backend (Python) and frontend (Jest) tests.

### Backend tests

```bash
# From the project root, with virtual environment active
pytest tests/ -v
```

Individual test files:

```bash
pytest tests/test_api.py -v           # Integration tests for all API endpoints
pytest tests/test_doc_builder.py -v   # Word document & HTML generation tests
pytest tests/test_utils.py -v         # Utility function tests
pytest tests/test_error_handling.py -v
pytest tests/test_resume_editing.py -v
```

### Frontend tests

```bash
cd frontend
npm test
```

---

## Project Structure

```
Resume-Generator/
├── main.py              # FastAPI application — all API routes and request handling
├── models.py            # SQLAlchemy ORM models (User, Resume tables)
├── database.py          # Database engine setup and session management
├── doc_builder.py       # Resume document builder (.docx + HTML preview)
├── prompts.py           # OpenAI system prompts and user prompt builders
├── utils.py             # Shared utility functions (sanitisation, validation, etc.)
├── seed_demo.py         # Standalone script to seed the demo user
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LandingPage.js    # Marketing homepage
│   │   │   ├── AuthPage.js       # Signup / login
│   │   │   ├── WizardPage.js     # Main resume generation wizard
│   │   │   └── MyResumesPage.js  # View, download, delete saved resumes
│   │   ├── components/           # Reusable React components
│   │   ├── services/api.js       # Axios HTTP client with interceptors
│   │   └── App.js                # Root component with routing
│   └── package.json              # Frontend dependencies
└── tests/
    ├── test_api.py
    ├── test_doc_builder.py
    ├── test_error_handling.py
    ├── test_resume_editing.py
    └── test_utils.py
```

---

## Deployment

### Backend (Render)

1. Create a new **Web Service** on [Render](https://render.com/).
2. Set the **Build Command** to `pip install -r requirements.txt`.
3. Set the **Start Command** to `uvicorn main:app --host 0.0.0.0 --port $PORT`.
4. Add the following environment variables in the Render dashboard:
   - `OPENAI_API_KEY` — your OpenAI API key
   - `DATABASE_URL` — Render PostgreSQL connection string (auto-provided if you add a PostgreSQL service)
   - `CORS_ORIGINS` — your frontend domain (e.g. `https://your-app.vercel.app`)

### Frontend (Vercel)

1. Connect your repository to [Vercel](https://vercel.com/).
2. Set the **Root Directory** to `frontend`.
3. Add the following environment variable in the Vercel dashboard:
   - `REACT_APP_API_URL` — your Render backend URL (e.g. `https://your-api.onrender.com`)

See `VERCEL_DEPLOYMENT.md` for a detailed step-by-step guide.

