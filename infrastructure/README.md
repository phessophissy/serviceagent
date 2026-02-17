# Infrastructure

This folder contains AWS SAM infrastructure definitions for Service Agent.

Resources provisioned:

- API Gateway HTTP API
- Lambda API backend
- DynamoDB tables: Users, Applications, ExtractedDocuments, AgentLogs
- S3 bucket for uploaded documents and extracted JSON
- Cognito User Pool + App Client

## Deploy

```bash
cd infrastructure
sam build --template-file template.yaml
sam deploy --guided
```

After deployment, copy outputs into `.env` and `frontend/.env.local`.
