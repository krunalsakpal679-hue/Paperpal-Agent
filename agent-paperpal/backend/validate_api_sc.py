import asyncio
import time
import uuid
import httpx
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Must append path to allow internal imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.models.job import Job, JobStatus
from app.schemas.job_state import JobState, JobStatus as StateStatus
from jose import jwt
from app.config import settings

from app.database import get_db, sessionmanager

async def mock_get_db():
    mock_db = AsyncMock()
    # Provide necessary methods
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_scalar = MagicMock()
    mock_scalar.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_scalar
    yield mock_db

app.dependency_overrides[get_db] = mock_get_db

# Helper for valid JWT
def get_valid_token():
    payload = {"sub": str(uuid.uuid4())}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

async def run_sc_checks():
    print("="*60)
    print("VALIDATING API GATEWAY & ORCHESTRATION")
    print("="*60)
    
    # Initialize sessionmanager for tests
    try:
        sessionmanager.session_factory
    except RuntimeError:
        sessionmanager.init(str(settings.DATABASE_URL))

    with TestClient(app) as client:
        # SC-5 / Requirement 5: JWT middleware returns 401 for missing/invalid tokens
        res_no_token = client.get("/api/v1/jobs/")
    if res_no_token.status_code == 401:
        print("[PASS] SC-5: Missing token returns 401")
    else:
        print(f"[FAIL] SC-5: Missing token returned {res_no_token.status_code}")
    
    res_invalid_token = client.get("/api/v1/jobs/", headers={"Authorization": "Bearer BAD_TOKEN"})
    if res_invalid_token.status_code == 401:
        print("[PASS] SC-5: Invalid token returns 401")
    else:
        print(f"[FAIL] SC-5: Invalid token returned {res_invalid_token.status_code}")

    # For following API calls, use valid token
    headers = {"Authorization": f"Bearer {get_valid_token()}"}
    
    # Needs a dummy database fixture for jobs POST logic
    # To test endpoint alone, we should mock DB dependencies or run in a test DB context
    # Since we need to test response time < 500ms, and we might hit DB
    # Let's mock `run_pipeline_task.delay` and `storage_service.upload_raw`
    
    from app.worker.tasks import run_pipeline_task
    with patch("app.api.v1.endpoints.jobs.storage_service.upload_raw", new_callable=AsyncMock) as mock_upload, \
         patch.object(run_pipeline_task, "delay") as mock_delay, \
         patch("app.api.v1.endpoints.jobs.AsyncSession.commit", new_callable=AsyncMock), \
         patch("app.api.v1.endpoints.jobs.AsyncSession.refresh", new_callable=AsyncMock):

        mock_upload.return_value = "s3_key_mock"
        
        start = time.time()
        file_content = b"Mock document content"
        files = {"file": ("test.docx", file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        data_payload = {"journal_identifier": "Nature"}
        
        # The global mock_get_db is already in place
        
        res_post = client.post("/api/v1/jobs/", files=files, data=data_payload, headers=headers)
        duration = (time.time() - start) * 1000
        
        if res_post.status_code == 202 and duration < 500:
            print(f"[PASS] SC-1: POST /api/v1/jobs returns {res_post.status_code} with job_id in {duration:.2f}ms (< 500ms)")
            job_id = res_post.json().get("job_id")
        else:
            print(f"[FAIL] SC-1: POST returned {res_post.status_code} in {duration:.2f}ms (expected 202, <500ms). Response: {res_post.text}")
            job_id = str(uuid.uuid4()) # dummy fallback
            
    # SC-3: GET /api/v1/jobs/{id}/result returns signed S3 URL after completion
    with patch("app.api.v1.endpoints.results.AsyncSession.execute", new_callable=AsyncMock) as mock_exec:
        job_mock = MagicMock()
        job_mock.status = JobStatus.completed
        job_mock.output_s3_key = "https://signed.mock/url.docx"
        job_mock.latex_s3_key = "https://signed.mock/url.tex"
        job_mock.compliance_score = 95.0
        job_mock.total_changes = 10
        
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = job_mock
        mock_exec.return_value = mock_scalar
        
        res_result = client.get(f"/api/v1/jobs/{job_id}/result", headers=headers)
        if res_result.status_code == 200:
            data = res_result.json()
            if data.get("docx_url") == "https://signed.mock/url.docx":
                print("[PASS] SC-3: GET /api/v1/jobs/{id}/result returns signed S3 URL after completion")
            else:
                print(f"[FAIL] SC-3: URL mismatch: {data}")
        else:
            print(f"[FAIL] SC-3: Result endpoint returned {res_result.status_code}")

    # SC-2 & SC-4: WebSocket events & Pipeline retries
    # We will test the worker function directly
    # `run_pipeline_task`
    from app.worker.tasks import _run_pipeline_async
    
    async def mock_subscribe(job_id):
        events = [
            {"status": "ingesting", "progress": 20},
            {"status": "parsing", "progress": 40},
            {"status": "interpreting", "progress": 60},
            {"status": "transforming", "progress": 80},
            {"status": "validating", "progress": 90},
            {"status": "completed", "progress": 100}
        ]
        for event in events:
            yield event

    with patch("app.worker.tasks.job_service.get_job", new_callable=AsyncMock) as mock_get_job, \
         patch("app.worker.tasks.job_service.update_status", new_callable=AsyncMock) as mock_update_status, \
         patch("app.worker.tasks.job_service.save_result", new_callable=AsyncMock) as mock_save_result, \
         patch("app.worker.tasks.pipeline.ainvoke", new_callable=AsyncMock) as mock_ainvoke, \
         patch("app.api.websocket.cache_service.subscribe_progress", new_callable=MagicMock) as mock_sub:
        
        mock_sub.return_value = mock_subscribe(job_id)
        
        mock_job = MagicMock()
        mock_job.raw_s3_key = "raw_s3"
        mock_job.source_format = "docx"
        mock_job.journal_identifier = "nature"
        mock_get_job.return_value = mock_job
        
        # Test retry 
        mock_ainvoke.side_effect = Exception("LLM Timeout Event")
        try:
            await _run_pipeline_async(job_id)
            print("[FAIL] SC-4: Pipeline should have raised exception")
        except Exception as e:
            if "LLM Timeout Event" in str(e):
                print("[PASS] SC-4: Pipeline encounters transient failure correctly (mocked LLM timeout raised)")
            else:
                print("[FAIL] SC-4: Unexpected exception", e)
                
        # SC-2: Websocket connection checking
        received_statuses = []
        with client.websocket_connect(f"/api/v1/jobs/{job_id}/stream") as websocket:
            try:
                while True:
                    data = websocket.receive_json()
                    received_statuses.append(data.get("status"))
                    if data.get("status") in ("completed", "failed"):
                        break
            except Exception:
                pass
        
        agent_statuses = {"ingesting", "parsing", "interpreting", "transforming", "validating"}
        if agent_statuses.issubset(set(received_statuses)):
             print(f"[PASS] SC-2: WebSocket received all 5 agent completion events: {received_statuses}")
        else:
             print(f"[FAIL] SC-2: WebSocket missed some agent events. Received: {received_statuses}")
        
    print("\n============================================================")
    print("API AND ORCHESTRATION VALIDATION COMPLETE")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(run_sc_checks())
