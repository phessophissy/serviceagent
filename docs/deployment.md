# AWS Deployment Guide

## Deploy Infrastructure

```bash
cd /home/thee1/dev/serviceagent/infrastructure
sam build --template-file template.yaml
sam deploy --guided
```

Record outputs:

- `ApiBaseUrl`
- `UserPoolId`
- `UserPoolClientId`
- `DocumentsBucketName`

## Configure Runtime Environment

Set Lambda environment variables if needed after deployment:

- `NOVA_SONIC_MODEL_ID`
- `NOVA_MULTIMODAL_MODEL_ID`
- `NOVA_LITE_MODEL_ID`
- `NOVA_ACT_MODEL_ID`
- `NOTIFICATION_SENDER_EMAIL`

## Frontend Deployment

Deploy `frontend/` to AWS Amplify Hosting or S3 + CloudFront.

Set frontend env vars:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_COGNITO_REGION`
- `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
- `NEXT_PUBLIC_COGNITO_CLIENT_ID`
