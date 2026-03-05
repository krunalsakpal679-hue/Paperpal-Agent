import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.services.cache_service import cache_service
from app.services.storage_service import storage_service
from app.schemas.jro_schema import JROSchema


@pytest.mark.asyncio
async def test_cache_service_miss_and_hit():
    with patch.object(cache_service.redis_client, "get", new_callable=AsyncMock) as mock_get:
        # Simulate MISS (Returns None)
        mock_get.return_value = None
        miss_result = await cache_service.get_jro("nonexistent_key")
        assert miss_result is None

        # Simulate HIT (Returns JRO JSON)
        mock_get.return_value = """
        {
            "journal_name": "Nature",
            "extraction_source": "web_scrape",
            "extraction_confidence": 0.95,
            "heading_rules": {"levels": {}},
            "abstract_rules": {"required_sections": []},
            "layout_rules": {"columns": 2, "margins": {}},
            "figure_rules": {"caption_position": "bottom"},
            "table_rules": {"caption_position": "top"},
            "section_requirements": {"required": [], "optional": []}
        }
        """
        hit_result = await cache_service.get_jro("nature")
        assert hit_result is not None
        assert isinstance(hit_result, JROSchema)
        assert hit_result.journal_name == "Nature"


@pytest.mark.asyncio
async def test_storage_service_upload_raw():
    # Patch the aioboto3 Session client context manager
    mock_s3_client_instance = AsyncMock()
    mock_s3_client_mgr = AsyncMock()
    mock_s3_client_mgr.__aenter__.return_value = mock_s3_client_instance

    with patch.object(storage_service.session, "client", return_value=mock_s3_client_mgr):
        # Call upload_raw
        key = await storage_service.upload_raw("job-uuid-1234", "manuscript.docx", b"dummy bits")
        
        # Verify it uploads to MinIO/S3 and returns valid key
        assert key == "jobs/job-uuid-1234/raw_manuscript.docx"
        
        # Verify arguments passed to put_object
        mock_s3_client_instance.put_object.assert_called_once_with(
            Bucket=storage_service.bucket,
            Key=key,
            Body=b"dummy bits"
        )
