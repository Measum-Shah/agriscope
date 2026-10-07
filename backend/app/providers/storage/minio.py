"""Abstract storage provider and concrete MinIO / Mock storage adapters."""

from __future__ import annotations

import io
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.core.config import settings
from app.core.logging import logger


class StorageProvider(ABC):
    """Abstract interface for object storage operations."""

    @abstractmethod
    async def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None,
    ) -> str:
        """Upload raw bytes to storage and return its resource URI / key."""
        pass

    @abstractmethod
    async def download_bytes(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        """Download raw bytes from storage."""
        pass

    @abstractmethod
    async def get_presigned_download_url(
        self,
        object_name: str,
        expires_in_seconds: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        """Generate a time-limited signed URL for direct client download."""
        pass


class MockStorageProvider(StorageProvider):
    """In-memory and local scratch storage adapter for test and offline development."""

    _storage: Dict[str, bytes] = {}

    async def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None,
    ) -> str:
        key = f"{bucket or settings.MINIO_DEFAULT_BUCKET}/{object_name}"
        self._storage[key] = data
        logger.info("MockStorageProvider: Uploaded object", key=key, size=len(data))
        return f"mock://{key}"

    async def download_bytes(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        key = f"{bucket or settings.MINIO_DEFAULT_BUCKET}/{object_name}"
        if key not in self._storage:
            # Fallback check by object_name alone
            for k, val in self._storage.items():
                if k.endswith(object_name):
                    return val
            raise FileNotFoundError(f"Object {object_name} not found in mock storage.")
        return self._storage[key]

    async def get_presigned_download_url(
        self,
        object_name: str,
        expires_in_seconds: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        key = f"{bucket or settings.MINIO_DEFAULT_BUCKET}/{object_name}"
        expiry_ts = int((datetime.utcnow() + timedelta(seconds=expires_in_seconds)).timestamp())
        token = uuid.uuid4().hex[:12]
        return f"/api/v1/reports/download/{object_name}?token={token}&expires={expiry_ts}"


class MinIOStorageProvider(StorageProvider):
    """Production S3-compatible object storage provider backed by MinIO."""

    def __init__(self):
        try:
            from minio import Minio
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_USE_SSL,
            )
            # Ensure default bucket exists
            bucket = settings.MINIO_DEFAULT_BUCKET
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
        except Exception as e:
            logger.warning("MinIO client initialization failed, falling back to mock", error=str(e))
            self.client = None

    async def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None,
    ) -> str:
        b_name = bucket or settings.MINIO_DEFAULT_BUCKET
        if not self.client:
            return await MockStorageProvider().upload_bytes(data, object_name, content_type, b_name)

        bio = io.BytesIO(data)
        self.client.put_object(
            b_name,
            object_name,
            bio,
            length=len(data),
            content_type=content_type,
        )
        return f"s3://{b_name}/{object_name}"

    async def download_bytes(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        b_name = bucket or settings.MINIO_DEFAULT_BUCKET
        if not self.client:
            return await MockStorageProvider().download_bytes(object_name, b_name)

        response = self.client.get_object(b_name, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def get_presigned_download_url(
        self,
        object_name: str,
        expires_in_seconds: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        b_name = bucket or settings.MINIO_DEFAULT_BUCKET
        if not self.client:
            return await MockStorageProvider().get_presigned_download_url(
                object_name, expires_in_seconds, b_name
            )

        return self.client.presigned_get_object(
            b_name,
            object_name,
            expires=timedelta(seconds=expires_in_seconds),
        )


def get_storage_provider() -> StorageProvider:
    """Factory creating configured storage provider."""
    if settings.STORAGE_PROVIDER == "minio":
        return MinIOStorageProvider()
    return MockStorageProvider()
