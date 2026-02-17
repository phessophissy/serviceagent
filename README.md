# Service Agent (SA)

Service Agent is a multi-agent AI service worker that completes real bureaucratic processes for users.

It is designed as a hackathon-grade production prototype for the AWS Amazon Nova Hackathon, with:

- Amazon Bedrock + Amazon Nova models
- Agentic workflow orchestration
- Multimodal document understanding
- Voice interview interaction
- Browser automation interface for Nova Act
- Serverless AWS-native backend

## Repository Structure

```text
serviceagent/
├── frontend/         # Next.js + Tailwind web app
├── backend/          # FastAPI on Lambda + orchestration services
├── agents/           # Specialized agent classes (5 agents)
├── automation/       # Nova Act automation controller
├── infrastructure/   # AWS SAM IaC template
├── docs/             # Setup and deployment guides
├── .env.example
└── README.md
```

## Multi-Agent Design

1. Interview Agent
- Uses Nova Sonic via Bedrock
- Conducts conversational intake and outputs structured profile JSON

2. Document Agent
- Uses Nova multimodal model via Bedrock
- Extracts fields from uploaded documents

3. Validation Agent
- Uses Nova Lite
- Detects missing/conflicting information and asks clarification questions

4. Automation Agent
- Uses Nova Act planning + automation controller
- Executes website form completion flow

5. Notification Agent
- Sends status updates and logs progress

## Backend API (Core Endpoints)

- `POST /applications`
- `POST /applications/{application_id}/interview-turn`
- `POST /applications/{application_id}/documents/upload-url`
- `POST /applications/{application_id}/documents/process`
- `POST /applications/{application_id}/validate`
- `POST /applications/{application_id}/automate`
- `GET /applications/{application_id}`
- `GET /applications/{application_id}/logs`

## Data Model

DynamoDB tables:

- `Users`
- `Applications`
- `ExtractedDocuments`
- `AgentLogs`

S3 objects:

- Raw uploaded documents (private)
- Extracted JSON outputs

## Security Defaults

- Cognito User Pool authentication (infrastructure scaffolded)
- Private S3 bucket with public access blocked
- Signed upload/download URLs only
- No public document read access

## Local Development

```bash
cd /home/thee1/dev/serviceagent
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. python -m backend.src.main
```

In another terminal:

```bash
cd /home/thee1/dev/serviceagent/frontend
npm install
npm run dev
```

Detailed instructions:

- `docs/setup.md`
- `docs/deployment.md`
