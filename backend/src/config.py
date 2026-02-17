import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    users_table: str = os.getenv("USERS_TABLE", "ServiceAgentUsers")
    applications_table: str = os.getenv("APPLICATIONS_TABLE", "ServiceAgentApplications")
    extracted_docs_table: str = os.getenv("EXTRACTED_DOCS_TABLE", "ServiceAgentExtractedDocuments")
    agent_logs_table: str = os.getenv("AGENT_LOGS_TABLE", "ServiceAgentAgentLogs")
    documents_bucket: str = os.getenv("DOCUMENTS_BUCKET", "")

    # Bedrock model identifiers are configurable because accounts/regions vary.
    nova_sonic_model_id: str = os.getenv("NOVA_SONIC_MODEL_ID", "amazon.nova-sonic-v1:0")
    nova_multimodal_model_id: str = os.getenv("NOVA_MULTIMODAL_MODEL_ID", "amazon.nova-pro-v1:0")
    nova_lite_model_id: str = os.getenv("NOVA_LITE_MODEL_ID", "amazon.nova-lite-v1:0")
    nova_act_model_id: str = os.getenv("NOVA_ACT_MODEL_ID", "amazon.nova-act-v1:0")

    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:3000")
    local_mode: bool = os.getenv("LOCAL_MODE", "false").lower() == "true"
    notification_sender_email: str = os.getenv("NOTIFICATION_SENDER_EMAIL", "")


settings = Settings()
