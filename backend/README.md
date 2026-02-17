# Backend

Serverless Python backend for Service Agent.

## Responsibilities

- API endpoints via FastAPI (deployed on Lambda via Mangum)
- Application state persistence in DynamoDB
- Secure document handling with S3 signed URLs
- Multi-agent orchestration with Bedrock Nova models
- Notification dispatch and agent activity logs

## Local Run

```bash
cd /home/thee1/dev/serviceagent
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. python -m backend.src.main
```

API available at `http://localhost:8000`.
