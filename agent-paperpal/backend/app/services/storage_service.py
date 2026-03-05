# backend/app/services/storage_service.py
"""
Storage service using aioboto3 for AWS S3 / MinIO integration.
"""

import aioboto3
from app.config import settings


class StorageService:
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.bucket = settings.AWS_S3_BUCKET
        self.endpoint_url = settings.AWS_S3_ENDPOINT_URL

    async def upload_raw(self, job_id: str, filename: str, file_bytes: bytes) -> str:
        """Upload raw document file for a specific job."""
        s3_key = f"jobs/{job_id}/raw_{filename}"
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            await s3.put_object(Bucket=self.bucket, Key=s3_key, Body=file_bytes)
        return s3_key

    async def upload_output(self, job_id: str, filename: str, file_bytes: bytes) -> str:
        """Upload final rendered output document."""
        s3_key = f"jobs/{job_id}/output_{filename}"
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            await s3.put_object(Bucket=self.bucket, Key=s3_key, Body=file_bytes)
        return s3_key

    async def download_raw(self, s3_key: str) -> bytes:
        """Download a raw file from S3."""
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=s3_key)
            return await response["Body"].read()

    async def get_signed_url(self, s3_key: str, expiry: int = 172800) -> str:
        """Generate a pre-signed URL to grant temporary access."""
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expiry,
            )
            return url


# Singleton
storage_service = StorageService()
