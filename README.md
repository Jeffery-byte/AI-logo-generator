# AI Logo Generator

A personal full-stack project that generates logo concepts from a business name,
description, audience, colors, and one of six styles. The app uses a Next.js 15 /
React 19 frontend and a FastAPI backend that calls Google Vertex AI Imagen.

[Video demo](https://github.com/user-attachments/assets/efe8987f-7ed7-40be-acd1-5b229683be02)

## Preview

![Logo creator](screenshots/Main%20interface/Screenshot%20%2819%29.png)
![Generated concepts](screenshots/Generated%20Logos/Screenshot%20%2822%29.png)

## Run locally

Requirements: Python 3.12, Node.js 22, npm, and a Google Cloud project with Vertex AI
API access, billing enabled, and access to the configured Imagen model. Model
availability depends on your project and region; check access before generating.

```sh
git clone https://github.com/Jeffery-byte/AI-logo-generator.git
cd AI-logo-generator
python -m venv backend/.venv
source backend/.venv/bin/activate
# Windows PowerShell: backend/.venv/Scripts/Activate.ps1
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Set `GOOGLE_CLOUD_PROJECT` in `backend/.env`. Authenticate locally with
`gcloud auth application-default login`. Keep downloaded service-account files
outside the repository. Google credentials authenticate the backend to Vertex AI;
the app does not implement end-user accounts.

Start the backend:

```sh
cd backend
uvicorn main:app --reload --port 8000
```

In another terminal, start the frontend:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. API documentation is at http://localhost:8000/docs.
The current frontend and backend are configured for these local addresses.

## How it works

1. The frontend sends validated business and style settings to FastAPI.
2. The backend builds a prompt and requests up to two variations from Vertex AI.
3. Image files are saved locally in `backend/generated_logos/` and served to the UI.

Generation incurs Google Cloud charges. Startup diagnostics are disabled by
default because the full diagnostic includes a real generation request. The
on-demand diagnostic endpoint also makes live provider calls. Set
`RUN_STARTUP_DIAGNOSTICS=true` only when you intend to run them.

## Project scope

This is a prototype with local file storage and an in-memory request limiter.
The UI displays configured cost estimates, not a billing reconciliation. Response
confidence values are not measured user-satisfaction scores. Throughput, latency,
and quality claims require a documented benchmark or evaluation.

The source for the frontend is in `frontend/src/app/` and
`frontend/src/components/`; the backend entry point is `backend/main.py`.
`compose.yaml` builds the backend container only; local Google credentials must be
provided separately to a container. The development commands above are the
primary setup path. Paid provider integration and production deployment hardening are follow-up work.

## Checks

```sh
python -m pip install -r backend/requirements-dev.txt
pytest backend/tests -q
python scripts/check_secrets.py
cd frontend
npm ci
npm audit
npm run lint
npm run build
```

The backend compatibility checks mock cloud authentication/provider behavior; they
do not measure live generation quality or performance. GitHub Actions runs the
build, dependency audits, tests, and a limited current-file credential pattern
check. Dependabot checks for dependency updates weekly. Historical credentials
must still be revoked at the provider; deleting source files does not revoke them.

The frontend temporarily overrides Next.js's PostCSS dependency and the
TypeScript parser's minimatch dependency to patched versions. The production
build and lint checks validate those overrides; remove them once upstream
versions resolve to the same patched dependencies without overrides.
