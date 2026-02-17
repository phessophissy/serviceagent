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

## 3. Run Backend Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. python -m backend.src.main
```

## 4. Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

## 5. Demo Sequence

1. Start a new scholarship application from the homepage.
2. Use voice intake to capture the request.
3. Upload a document from the application page.
4. Trigger validation and automation endpoints from API client / UI extensions.
5. Observe logs in dashboard timeline.
