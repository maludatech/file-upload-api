import uuid
from typing import BinaryIO

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import settings

_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    region_name=settings.s3_region,
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key,
    config=BotoConfig(signature_version="s3v4"),
)


def build_storage_key(user_id: uuid.UUID, filename: str) -> str:
    return f"{user_id}/{uuid.uuid4()}_{filename}"


def upload_fileobj(fileobj: BinaryIO, storage_key: str, content_type: str) -> None:
    _client.upload_fileobj(
        fileobj,
        settings.s3_bucket_name,
        storage_key,
        ExtraArgs={"ContentType": content_type},
    )


def download_fileobj(storage_key: str) -> BinaryIO:
    response = _client.get_object(Bucket=settings.s3_bucket_name, Key=storage_key)
    return response["Body"]


def delete_object(storage_key: str) -> None:
    _client.delete_object(Bucket=settings.s3_bucket_name, Key=storage_key)


def object_exists(storage_key: str) -> bool:
    try:
        _client.head_object(Bucket=settings.s3_bucket_name, Key=storage_key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise
