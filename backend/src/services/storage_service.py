import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3

from backend.src.config import settings


class StorageService:
    def __init__(self) -> None:
        self.s3 = boto3.client("s3", region_name=settings.aws_region)
        self.bucket = settings.documents_bucket

    @staticmethod
    def now_prefix() -> str:
        return datetime.now(timezone.utc).strftime("%Y/%m/%d")

    def build_document_key(self, user_id: str, application_id: str, file_name: str) -> str:
        return f"documents/{self.now_prefix()}/{user_id}/{application_id}/{file_name}"

    def create_upload_url(self, s3_key: str, content_type: str) -> str:
        return self.s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=900,
        )

    def write_extracted_json(self, key: str, payload: dict) -> None:
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )

    def upload_artifact_bytes(self, *, key: str, body: bytes, content_type: str = "image/png") -> str:
        self.s3.put_object(
            Bucket=settings.artifacts_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
        return key

    def generate_download_url(self, s3_key: str, bucket: str | None = None) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket or self.bucket, "Key": s3_key},
            ExpiresIn=900,
        )

    def download_document_to_tempfile(self, s3_key: str, suffix: str = ".bin") -> str:
        response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
        body = response["Body"].read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(body)
            return str(Path(tmp_file.name))
