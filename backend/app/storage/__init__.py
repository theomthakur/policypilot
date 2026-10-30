"""Where uploaded PDFs live. Local disk by default; an S3-compatible bucket lets the API and the workers run
on different nodes (docs/adr/0010). Metadata (owner, checksum, key) stays in PostgreSQL; downloads are
authorized by the API, never by a bucket URL."""

import asyncio
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class Storage(Protocol):
    name: str

    def put(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes | None: ...


class LocalStorage:
    name = "local"

    def __init__(self, base: str) -> None:
        self.base = Path(base)

    def put(self, key: str, data: bytes) -> None:
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / key).write_bytes(data)

    def read(self, key: str) -> bytes | None:
        path = self.base / key
        return path.read_bytes() if path.is_file() and path.parent.resolve() == self.base.resolve() else None


class S3Storage:
    name = "s3"

    def __init__(self, bucket: str, endpoint: str, region: str, access_key: str, secret_key: str) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            config=Config(
                signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 3}
            ),
        )

    def ensure_bucket(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, data: bytes) -> None:
        self.ensure_bucket()
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="application/pdf")

    def read(self, key: str) -> bytes | None:
        from botocore.exceptions import ClientError

        try:
            return bytes(self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read())
        except ClientError:
            return None


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    if s.storage_backend == "s3":
        return S3Storage(s.s3_bucket, s.s3_endpoint, s.s3_region, s.s3_access_key, s.s3_secret_key)
    return LocalStorage(s.upload_dir)


async def put(key: str, data: bytes) -> None:
    await asyncio.to_thread(get_storage().put, key, data)


async def read(key: str) -> bytes | None:
    return await asyncio.to_thread(get_storage().read, key)


@contextmanager
def local_copy(key: str, data: bytes) -> Iterator[Path]:
    """A temporary file holding `data`, for parsers that need a path."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / key
        path.write_bytes(data)
        yield path
