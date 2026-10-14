"""
S3-compatible object storage (AWS, MinIO) behind the Connector
protocol. boto3 is synchronous, so every call runs in a worker thread
to keep the async surface honest.

    async with S3Connector(endpoint="http://localhost:9000") as s3:
        await s3.ensure_bucket("artifacts")
        await s3.put("artifacts", "runs/1.json", b"{}")
        data = await s3.get("artifacts", "runs/1.json")
"""

import asyncio
from typing import Any

import boto3

from plyght.connector import Connector
from plyght.settings import ConnectorSettings, connector_config


class S3Settings(ConnectorSettings):
    """
    Credentials and endpoint; PLYGHT_S3_* in the environment. Leave
    endpoint unset for AWS, or point it at MinIO or any S3 compatible
    store.
    """

    model_config = connector_config("s3")

    endpoint: str | None = None
    region: str = "us-east-1"
    access_key: str | None = None
    secret_key: str | None = None


class S3Connector(Connector):
    """
    Thin object-store operations over a boto3 client. Anything not
    surfaced here is one .client call away.
    """

    Settings = S3Settings

    async def connect(self) -> None:
        """Build the boto3 client (no network round trip yet)."""
        self._client = await asyncio.to_thread(
            boto3.client,
            "s3",
            endpoint_url=self.settings.endpoint,
            region_name=self.settings.region,
            aws_access_key_id=self.settings.access_key,
            aws_secret_access_key=self.settings.secret_key,
        )
        self.log.debug("connected", extra={"endpoint": self.settings.endpoint})

    async def aclose(self) -> None:
        """boto3 clients hold no persistent connection; just drop it."""
        self._client = None

    async def healthy(self) -> bool:
        """List buckets as the cheapest authenticated round trip."""
        try:
            await asyncio.to_thread(self.client.list_buckets)
            return True
        except Exception:
            return False

    async def ensure_bucket(self, bucket: str) -> None:
        """Create the bucket if it does not already exist."""

        def _ensure() -> None:
            try:
                self.client.head_bucket(Bucket=bucket)
            except Exception:
                self.client.create_bucket(Bucket=bucket)

        await asyncio.to_thread(_ensure)

    async def put(self, bucket: str, key: str, data: bytes) -> None:
        """Write one object."""
        await asyncio.to_thread(
            self.client.put_object, Bucket=bucket, Key=key, Body=data
        )

    async def get(self, bucket: str, key: str) -> bytes:
        """Read one object's bytes."""

        def _get() -> bytes:
            return self.client.get_object(Bucket=bucket, Key=key)["Body"].read()

        return await asyncio.to_thread(_get)

    async def list(self, bucket: str, prefix: str = "") -> list[dict[str, Any]]:
        """Every object under a prefix, across pages: [{key, size, modified}]."""

        def _list() -> list[dict[str, Any]]:
            pages = self.client.get_paginator("list_objects_v2").paginate(
                Bucket=bucket, Prefix=prefix
            )
            return [
                {
                    "key": entry["Key"],
                    "size": entry["Size"],
                    "modified": entry["LastModified"],
                }
                for page in pages
                for entry in page.get("Contents", [])
            ]

        return await asyncio.to_thread(_list)

    async def delete(self, bucket: str, key: str) -> None:
        """Delete one object."""
        await asyncio.to_thread(self.client.delete_object, Bucket=bucket, Key=key)
