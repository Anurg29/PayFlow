# PayFlow

A modern fintech-grade payment backend and frontend stack.

## Overview

- **Backend:** FastAPI (Python), SQLAlchemy ORM, JWT Auth, Caching, Admin/Merchant/User roles, Transaction state machine, Anomaly detection
- **Frontend:** React (Vite), modern UI, admin dashboard, payment form, transaction views
- **Database:** PostgreSQL (preferred), SQLite fallback for local/dev

---

## Project Structure

```
PayFlow/
├── app/                # FastAPI backend
│   ├── main.py         # FastAPI entrypoint
│   ├── database.py     # SQLAlchemy DB setup
│   ├── models.py       # ORM models
│   ├── ...             # Routers, schemas, admin, auth, transactions
├── frontend/           # React frontend (Vite)
│   ├── src/            # React source code
│   ├── public/         # Static assets
│   └── ...
├── requirements.txt    # Python backend dependencies
├── .env.example        # Example environment variables
├── netlify.toml        # Netlify config (frontend)
├── render.yaml         # Render.com config (backend)
└── README.md           # (this file)
```

---

## Backend Setup (FastAPI)

### 1. Python Environment

- Python 3.9+
- Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in your database credentials:

```
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname?sslmode=require
```
- For local dev, you can omit `DATABASE_URL` to use SQLite.

### 3. Run Backend Locally

```bash
uvicorn app.main:app --reload
```
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Test Database Connection

```bash
python -m app.db_test
```

---

## Frontend Setup (React + Vite)

### 1. Install Node.js dependencies

```bash
cd frontend
npm install
```

### 2. Run Frontend Locally

```bash
npm run dev
```
- App: [http://localhost:5173](http://localhost:5173)

---

## Deployment

- **Backend:** Deploy to Render.com (see `render.yaml`) or any service supporting Python/FastAPI.
- **Frontend:** Deploy to Netlify, Vercel, or any static host (see `netlify.toml`).
- Set `DATABASE_URL` and any secrets in your deployment environment.

---

## Key Features

- Real-time payment transaction API
- Multi-method payment routing
- Transaction state machine
- Anomaly detection & flagging
- JWT authentication (admin/merchant/user)
- Admin dashboard
- In-memory caching
- Idempotency keys

---

## Useful Commands

- Run backend: `uvicorn app.main:app --reload`
- Run frontend: `cd frontend && npm run dev`
- Test DB: `python -m app.db_test`

---

## License

MIT License. See LICENSE file if present.
