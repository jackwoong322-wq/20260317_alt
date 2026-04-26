# Project Agent Guide

This file is the **primary source of truth** for all coding agents in this repository.
Tool-specific files (`.cursorrules`, `CLAUDE.md`, etc.) should stay thin and defer to this file.

---

## Tech Stack

- **Frontend**: React 18, Vite 5
  - `03_frontend/`: TypeScript + TSX
  - `04_frontend_0222fb/`: JavaScript + JSX
- **Backend**: Python 3.13, FastAPI, Uvicorn
- **Database/Auth**: Supabase Postgres, Supabase Auth, Edge Functions with Deno
- **Infra**: Vercel (frontend), Render (backend), GitHub Actions (automation)

---

## Project Structure

- `03_frontend/`: React 18 + Vite 5 (TypeScript) — Vercel 배포
- `04_frontend_0222fb/`: React 18 + Vite 5 (JavaScript) — Vercel 배포
- `02_backend/`: FastAPI + Uvicorn — Render 배포 (`https://two0260317-alt.onrender.com`)
- `01_pairUSDT/`: Python scripts — Binance OHLCV 수집, 사이클 분석, 예측
- `supabase/functions/`: Supabase Edge Functions (Deno)
- `reports/`: 작업 보고서
- `temp/`: 임시 작업 파일 (이슈번호별 폴더)

---

## Frontend Rules

Applies to `03_frontend/` and `04_frontend_0222fb/`.

- Use functional components and hooks only.
- Use `fetch` for API calls.
- Read the backend base URL from `VITE_API_URL` environment variable.
- Use `lightweight-charts` for chart rendering.
- Use ESM imports only. Do not use CommonJS `require()`.
- Frontend environment variables must use the `VITE_` prefix.
- Legacy analyzer assets live under `public/legacy/` and should be treated as production assets.
- `03_frontend/` specific: keep aligned with legacy analyzer UI (`01_pairUSDT/033_visualizer_html.py`).

---

## Backend Rules

Applies to `02_backend/`.

- Use FastAPI with type hints on all endpoints.
- Use Pydantic models for all request and response schemas.
- Use the Supabase Python client for database operations. Do not write raw SQL unless explicitly asked.
- Load environment variables with `python-dotenv`.
- Keep CORS aligned with the deployed Vercel frontend origin.
- Organize routers by domain (e.g. `routers/ohlcv.py`).
- Return structured JSON responses consistently.

---

## Supabase Rules

- Use Supabase client libraries instead of direct PostgreSQL connections.
- Enable RLS on every table.
- Use Supabase Auth for authentication.
- In Edge Functions, use the Deno runtime and import from `supabase-js`.

---

## OHLCV Script Rules

Applies to `01_pairUSDT/`.

- Use pandas for data processing.
- Fetch market data through the Binance REST API.
- Store and process timestamps in UTC only.
- Keep scripts runnable both standalone and through GitHub Actions.

---

## GitHub Actions Rules

- Workflows live in `.github/workflows/`.
- Pipeline file: `pipeline.yml` (collect: daily 00:00 UTC / analyze: weekly Mon 01:00 UTC)
- Never hardcode secrets. Use repository or environment secrets.

---

## General Coding Rules

- Never hardcode API keys, URLs, or secrets.
- Prefer descriptive variable names: `is_loading`, `has_error`, `is_active`.
- Keep functions focused and small.
- Handle errors explicitly with `try/catch` or `try/except`.
- Add comments only for non-obvious logic.

---

## Error Handling Rules

- Identify the root cause before fixing.
- After a fix, verify both the failure path and the happy path.
- If the same error repeats more than twice, stop patching symptoms and address the root cause.
- For import errors: check module paths before changing code broadly.
- For FastAPI `422` errors: inspect the Pydantic schema and request shape first.
- For CORS issues: verify backend config before changing frontend calls.

---

## Working Agreement

- AGENTS.md is the single source of truth. Keep tool-specific files lightweight.
- Claude Code workflow rules are in `CLAUDE.md`.
- Test rules are in `test_rules.md`.
- Workflow rules are in `workflow_rules.md`.
