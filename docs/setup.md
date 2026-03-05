# Setup Guide

## 1. Prerequisites

- Python 3.12+
- Node.js 20+
- AWS CLI v2
- SAM CLI
- Bedrock model access enabled in your AWS account

## 2. Configure Environment

```bash
cd /home/thee1/dev/serviceagent
cp .env.example .env
```

Set the Bedrock Nova model IDs that exist in your account/region.
Set `DEMO_MODE=true` to enable the International Scholarship demo flow.
Ensure `APP_BASE_URL` points to the frontend host (default `http://localhost:3000`).

## 3. Run Backend Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
playwright install chromium
./scripts/run_local.sh
```

`run_local.sh` automatically:
- activates `.venv`
- loads `.env`
- bootstraps DynamoDB + S3 via `backend/scripts/bootstrap_aws_resources.py`
- starts Uvicorn on `http://localhost:8000`

## 4. Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

## 5. Demo Sequence

1. Start a new scholarship application from the homepage.
2. Enable `Demo Narrative Mode: International Scholarship Application`.
3. Start `Live Voice Interview` on the application detail page (WebSocket route: `/ws/interview/{application_id}`).
4. Upload required documents shown in the missing requirements panel.
5. Let planner advance to automation and observe screenshots in the timeline.
6. Review planner reasoning and task progression in the `AI Thinking Panel`.
