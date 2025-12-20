from __future__ import annotations

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings


class ObjectStorage:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: BaseClient | None = None

    @property
    def client(self) -> BaseClient:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.settings.s3_endpoint_url,
                region_name=self.settings.s3_region_name,
                aws_access_key_id=self.settings.s3_access_key_id,
                aws_secret_access_key=self.settings.s3_secret_access_key,
            )
        return self._client

    async def put_package(self, key: str, data: bytes, checksum: str) -> str:
        await run_in_threadpool(self._ensure_bucket)
        await run_in_threadpool(
            self.client.put_object,
            Bucket=self.settings.s3_bucket_name,
            Key=key,
            Body=data,
            ContentType="application/octet-stream",
            ServerSideEncryption="AES256",
            Metadata={"sha256": checksum},
        )
        return key

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.settings.s3_bucket_name)
        except ClientError as error:
            status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status not in {404, 400}:
                raise
            self.client.create_bucket(Bucket=self.settings.s3_bucket_name)
