"""
storage.py — MinIO client initialization and household folder management.
All object-storage interactions are contained here.
"""
import io
import logging
from typing import Optional

from minio import Minio
from minio.error import S3Error

from config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE, MINIO_BUCKETS

logger = logging.getLogger(__name__)

_minio_client: Optional[Minio] = None


def get_minio_client() -> Optional[Minio]:
    """
    Lazy-initializes the MinIO client singleton and ensures all required
    buckets exist. Returns None if MinIO is unreachable (non-fatal).
    """
    global _minio_client
    if _minio_client is not None:
        return _minio_client

    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        for bucket in MINIO_BUCKETS:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info(f"MinIO: created bucket '{bucket}'.")
        _minio_client = client
        logger.info(f"MinIO client initialized (endpoint={MINIO_ENDPOINT}).")
        return _minio_client
    except Exception as exc:
        logger.warning(f"MinIO initialization failed (service may be unavailable): {exc}")
        return None


def ensure_household_folders(household_hash: str) -> None:
    """
    Creates zero-byte placeholder objects in MinIO to establish the folder
    structure for a new household. This is idempotent — safe to call repeatedly.

    Folder layout:
        verified-docs/<hash>/raw_docs/
        verified-docs/<hash>/approved/
        verified-docs/<hash>/rejected/
        filled-forms/<hash>/filled_forms/
    """
    client = get_minio_client()
    if not client:
        logger.warning(f"Cannot create household folders for {household_hash[:16]}… — MinIO unavailable.")
        return

    placeholders = [
        ("verified-docs", f"{household_hash}/raw_docs/.keep"),
        ("verified-docs", f"{household_hash}/approved/.keep"),
        ("verified-docs", f"{household_hash}/rejected/.keep"),
        ("filled-forms",  f"{household_hash}/filled_forms/.keep"),
    ]

    for bucket, key in placeholders:
        if bucket not in MINIO_BUCKETS:
            continue
        try:
            client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=io.BytesIO(b""),
                length=0,
                content_type="application/octet-stream",
            )
        except S3Error:
            # Placeholder already exists — this is expected and safe to ignore.
            pass
        except Exception as exc:
            logger.warning(f"Could not write placeholder {bucket}/{key}: {exc}")
