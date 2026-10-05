"""
File storage service with multiple backend support.

Supports local filesystem, S3, and MinIO.
"""

import os
import shutil
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, List, Optional
from urllib.parse import urljoin

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


@dataclass
class FileInfo:
    """File metadata."""
    key: str
    name: str
    size: int
    content_type: str
    created_at: datetime
    url: Optional[str] = None
    etag: Optional[str] = None
    metadata: Optional[dict] = None


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> FileInfo:
        """Upload file and return metadata."""

    @abstractmethod
    async def download(self, key: str) -> Optional[BinaryIO]:
        """Download file."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if file exists."""

    @abstractmethod
    async def get_info(self, key: str) -> Optional[FileInfo]:
        """Get file metadata."""

    @abstractmethod
    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
    ) -> Optional[str]:
        """Generate presigned URL."""

    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> List[FileInfo]:
        """List files with prefix."""


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str = "./storage", base_url: str = "/files"):
        self.base_path = Path(base_path).resolve()
        self.base_url = base_url
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get full filesystem path for key."""
        return self.base_path / key

    def _get_url(self, key: str) -> str:
        """Get public URL for key."""
        return urljoin(self.base_url, key)

    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> FileInfo:
        file_path = self._get_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file, f)

        stat = file_path.stat()
        return FileInfo(
            key=key,
            name=Path(key).name,
            size=stat.st_size,
            content_type=content_type,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            url=self._get_url(key),
            metadata=metadata,
        )

    async def download(self, key: str) -> Optional[BinaryIO]:
        file_path = self._get_path(key)
        if not file_path.exists():
            return None
        return open(file_path, "rb")

    async def delete(self, key: str) -> bool:
        file_path = self._get_path(key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        return self._get_path(key).exists()

    async def get_info(self, key: str) -> Optional[FileInfo]:
        file_path = self._get_path(key)
        if not file_path.exists():
            return None

        stat = file_path.stat()
        return FileInfo(
            key=key,
            name=Path(key).name,
            size=stat.st_size,
            content_type="application/octet-stream",
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            url=self._get_url(key),
        )

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
    ) -> Optional[str]:
        if not await self.exists(key):
            return None
        return self._get_url(key)

    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> List[FileInfo]:
        files = []
        search_path = self.base_path / prefix

        if search_path.is_dir():
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.base_path)
                    info = await self.get_info(str(rel_path))
                    if info:
                        files.append(info)
                        if len(files) >= max_results:
                            break
        return files


class S3StorageBackend(StorageBackend):
    """S3/MinIO storage backend."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        region: str = "us-east-1",
        base_url: Optional[str] = None,
    ):
        self.endpoint_url = endpoint_url
        self.bucket = bucket
        self.region = region
        self.base_url = base_url

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

        # Ensure bucket exists
        try:
            self.s3_client.head_bucket(Bucket=bucket)
        except ClientError:
            self.s3_client.create_bucket(Bucket=bucket)

    def _get_url(self, key: str) -> str:
        if self.base_url:
            return urljoin(self.base_url, key)
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> FileInfo:
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        self.s3_client.upload_fileobj(file, self.bucket, key, ExtraArgs=extra_args)

        # Get object info
        response = self.s3_client.head_object(Bucket=self.bucket, Key=key)

        return FileInfo(
            key=key,
            name=Path(key).name,
            size=response["ContentLength"],
            content_type=content_type,
            created_at=response["LastModified"],
            url=self._get_url(key),
            etag=response.get("ETag", "").strip('"'),
            metadata=metadata,
        )

    async def download(self, key: str) -> Optional[BinaryIO]:
        try:
            import io
            buffer = io.BytesIO()
            self.s3_client.download_fileobj(self.bucket, key, buffer)
            buffer.seek(0)
            return buffer
        except ClientError:
            return None

    async def delete(self, key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    async def exists(self, key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    async def get_info(self, key: str) -> Optional[FileInfo]:
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return FileInfo(
                key=key,
                name=Path(key).name,
                size=response["ContentLength"],
                content_type=response.get("ContentType", "application/octet-stream"),
                created_at=response["LastModified"],
                url=self._get_url(key),
                etag=response.get("ETag", "").strip('"'),
                metadata=response.get("Metadata"),
            )
        except ClientError:
            return None

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
    ) -> Optional[str]:
        if not await self.exists(key):
            return None

        try:
            if method == "GET":
                return self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expiration,
                )
            elif method == "PUT":
                return self.s3_client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expiration,
                )
        except ClientError:
            pass
        return None

    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> List[FileInfo]:
        files = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if len(files) >= max_results:
                    break
                info = await self.get_info(obj["Key"])
                if info:
                    files.append(info)
        return files


class StorageService:
    """
    High-level storage service with automatic backend selection.

    Features:
    - Multiple backend support
    - Automatic key generation
    - Content-type detection
    - Presigned URLs
    """

    def __init__(self):
        self.backend: Optional[StorageBackend] = None
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Initialize storage backend based on config."""
        storage_type = settings.STORAGE_TYPE.lower()

        if storage_type == "s3" or settings.S3_ENDPOINT_URL:
            self.backend = S3StorageBackend(
                endpoint_url=settings.S3_ENDPOINT_URL,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                bucket=settings.S3_BUCKET,
                region=settings.S3_REGION,
            )
        elif storage_type == "minio":
            self.backend = S3StorageBackend(
                endpoint_url=settings.S3_ENDPOINT_URL,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                bucket=settings.S3_BUCKET,
                region=settings.S3_REGION,
            )
        else:
            self.backend = LocalStorageBackend(
                base_path=settings.STORAGE_LOCAL_PATH,
                base_url="/files",
            )

    def _generate_key(self, filename: str, prefix: str = "") -> str:
        """Generate unique storage key."""
        ext = Path(filename).suffix.lower()
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{prefix}{timestamp}/{unique_id}{ext}"

    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename."""
        import mimetypes
        return mimetypes.guess_type(filename)[0] or "application/octet-stream"

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        prefix: str = "",
        metadata: Optional[dict] = None,
    ) -> FileInfo:
        """Upload file with automatic key generation."""
        key = self._generate_key(filename, prefix)
        content_type = self._get_content_type(filename)
        return await self.backend.upload(file, key, content_type, metadata)

    async def upload_with_key(
        self,
        file: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> FileInfo:
        """Upload file with specific key."""
        return await self.backend.upload(file, key, content_type, metadata)

    async def download(self, key: str) -> Optional[BinaryIO]:
        """Download file."""
        return await self.backend.download(key)

    async def delete(self, key: str) -> bool:
        """Delete file."""
        return await self.backend.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        return await self.backend.exists(key)

    async def get_info(self, key: str) -> Optional[FileInfo]:
        """Get file metadata."""
        return await self.backend.get_info(key)

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
    ) -> Optional[str]:
        """Generate presigned URL."""
        return await self.backend.generate_presigned_url(key, expiration, method)

    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> List[FileInfo]:
        """List files with prefix."""
        return await self.backend.list_files(prefix, max_results)


# Global storage instance
storage_service = StorageService()


async def get_storage() -> StorageService:
    """Dependency for storage service."""
    return storage_service