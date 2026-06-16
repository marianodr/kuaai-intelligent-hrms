import io
from minio import Minio

_client: Minio | None = None
_bucket: str = "documents"


def init_client(settings) -> None:
    global _client, _bucket
    _client = Minio(
        f"{settings.minio_endpoint}:{settings.minio_port}",
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )
    _bucket = settings.minio_bucket_documents


def download_to_bytes(object_name: str) -> bytes:
    response = _client.get_object(_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_bytes(object_name: str, data: bytes, content_type: str = "application/pdf") -> None:
    _client.put_object(
        _bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def delete_object(object_name: str) -> None:
    _client.remove_object(_bucket, object_name)


def get_bytes(object_name: str) -> tuple[bytes, str]:
    """Returns (content_bytes, content_type)."""
    response = _client.get_object(_bucket, object_name)
    try:
        data = response.read()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        return data, content_type
    finally:
        response.close()
        response.release_conn()
