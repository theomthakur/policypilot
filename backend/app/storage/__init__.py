"""PDF originals: local disk, S3, or PostgreSQL for a small hosted demo without persistent disk.

Metadata (owner, checksum, key) stays in PostgreSQL; the API authorizes every download.
"""

import asyncio
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import psycopg
from psycopg.conninfo import make_conninfo

from app.config import Settings, get_settings


class Storage(Protocol):
    name: str

    def put(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes | None: ...

    def delete(self, key: str) -> None: ...


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

    def delete(self, key: str) -> None:
        path = self.base / key
        if path.is_file() and path.parent.resolve() == self.base.resolve():
            path.unlink()


class PostgresStorage:
    name = "postgres"

    def __init__(self, settings: Settings) -> None:
        self._conninfo = make_conninfo(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            connect_timeout=10,
        )

    def put(self, key: str, data: bytes) -> None:
        with psycopg.connect(self._conninfo) as connection:
            connection.execute(
                "INSERT INTO stored_pdfs (storage_name, data) VALUES (%s, %s) "
                "ON CONFLICT (storage_name) DO UPDATE SET data = EXCLUDED.data",
                (key, data),
            )

    def read(self, key: str) -> bytes | None:
        with psycopg.connect(self._conninfo) as connection:
            row = connection.execute(
                "SELECT data FROM stored_pdfs WHERE storage_name = %s", (key,)
            ).fetchone()
        return bytes(row[0]) if row is not None else None

    def delete(self, key: str) -> None:
        """Remove the original bytes after the authorized document record is deleted."""
        with psycopg.connect(self._conninfo) as connection:
            connection.execute("DELETE FROM stored_pdfs WHERE storage_name = %s", (key,))


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

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


@lru_cache
def _s3(bucket: str, endpoint: str, region: str, access_key: str, secret_key: str) -> S3Storage:
    return S3Storage(bucket, endpoint, region, access_key, secret_key)


def get_storage() -> Storage:
    s = get_settings()
    if s.storage_backend == "postgres":
        return PostgresStorage(s)
    if s.storage_backend == "s3":
        return _s3(s.s3_bucket, s.s3_endpoint, s.s3_region, s.s3_access_key, s.s3_secret_key)
    return LocalStorage(s.upload_dir)  # cheap, and always follows the current UPLOAD_DIR


async def put(key: str, data: bytes) -> None:
    await asyncio.to_thread(get_storage().put, key, data)


async def read(key: str) -> bytes | None:
    return await asyncio.to_thread(get_storage().read, key)


async def delete(key: str) -> None:
    await asyncio.to_thread(get_storage().delete, key)


@contextmanager
def local_copy(key: str, data: bytes) -> Iterator[Path]:
    """A temporary file holding `data`, for parsers that need a path."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / key
        path.write_bytes(data)
        yield path
