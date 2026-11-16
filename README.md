# NearMiss AI

Industrial Near-Miss Memory Agent — a prototype that records reported near-misses, retains experience in Hindsight, recalls relevant history, and presents evidence for qualified human review.

> **Safety:** Prototype only. Not certified and not a diagnostic tool. It never authorizes equipment restart. All bundled sample records are synthetic.

## What's included

- **Overview:** incident totals, open follow-ups, memory connection status, and recent activity.
- **Incident records:** add and view records, search by incident/machine/description, and filter by status.
- **Investigation:** submit an observation, optionally recall Hindsight memories, and view an advisory investigation brief.
- **Safety review:** human-review prompts and a form to save follow-up feedback.
- Responsive layout, form validation, loading states, and clear success/error messages.

## Run locally

Prerequisites: Python 3.10+, Node.js 18+ and npm.

### 1. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Add Hindsight credentials to .env if you want persistent memory recall.
# GROQ_API_KEY is optional; without it, the API returns a safe advisory fallback.
uvicorn app.main:app --reload --port 8000
```

### 2. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (usually http://localhost:5173).

If your backend runs somewhere other than `http://localhost:8000`, create `frontend/.env` and set:

```env
VITE_API_URL=http://localhost:8000
```

### 3. Load sample records

Use **Load sample records** on the overview, or run:

```bash
curl -X POST http://localhost:8000/demo/seed
```

The seed endpoint skips incident IDs that already exist, so loading samples more than once will not duplicate them.

## Tests

```bash
cd backend
pytest -q
```

Frontend production build:

```bash
cd frontend
npm run build
```

API docs are available at http://localhost:8000/docs.

## Hindsight and Groq

The app uses the Hindsight Python SDK for experience retention and recall. Configure `HINDSIGHT_BASE_URL`, `HINDSIGHT_API_KEY`, and `HINDSIGHT_BANK_ID` in `backend/.env`. Configure `GROQ_API_KEY` to enable optional language-model synthesis. Check `/health` and the investigation response before assuming memory recall or model synthesis was available.

SQLite remains the structured source of truth. Hindsight is the experience-memory layer. If Hindsight is not configured, incident records and the rest of the app still work.

## Limitations

No authentication or tenant isolation; use synthetic data only. Similarity is not proof of a shared root cause. LLM output is advisory and requires qualified review. No safety certification or operational validation.

## Submission links

- GitHub: add URL
- Article: add URL
- Reddit: add URL
- Video: add URL

MIT License.
