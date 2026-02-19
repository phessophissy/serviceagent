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

1. Planner Agent
- Uses Nova Lite via Bedrock
- Builds and updates a dynamic task plan, chooses next agent action, and tracks missing requirements

2. Interview Agent
- Uses Nova Sonic via Bedrock
- Conducts conversational intake and outputs structured profile JSON

3. Document Agent
- Uses Nova multimodal model via Bedrock
- Extracts fields from uploaded documents

4. Validation Agent
- Uses Nova Lite
- Detects missing/conflicting information and asks clarification questions

5. Automation Agent
- Uses Nova Act planning + automation controller
- Executes website form completion flow

6. Notification Agent
- Sends status updates and logs progress

## Demo Narrative Mode

Service Agent includes a preconfigured demo scenario:

- `international_scholarship_application`
- Preloaded planning knowledge base
- Demo automation target URL for reliable submission walkthrough (`/demo-scholarship-form`)
- Dynamic missing requirements workflow (`passport`, `academic_transcript`)

## Backend API (Core Endpoints)

- `POST /applications`
- `POST /applications/{application_id}/interview-turn`
- `POST /applications/{application_id}/documents/upload-url`
- `POST /applications/{application_id}/documents/process`
- `POST /applications/{application_id}/validate`
- `POST /applications/{application_id}/automate`
- `GET /applications/{application_id}`
- `GET /applications/{application_id}/logs`
- `GET /applications/{application_id}/timeline`
- `GET /planner/state/{application_id}`
- `WS /ws/interview/{application_id}`

## Data Model

DynamoDB tables:

- `Users`
- `Applications`
- `ExtractedDocuments`
- `AgentLogs`
- `PlannerState`
- `AutomationTimeline`

S3 objects:

- Raw uploaded documents (private)
- Extracted JSON outputs
- Automation screenshots (demo artifacts)

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
