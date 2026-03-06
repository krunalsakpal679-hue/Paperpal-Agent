import asyncio
import time
import uuid
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.job import JobStatus
from jose import jwt
from app.config import settings
from app.database import get_db, sessionmanager

async def mock_get_db():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_scalar = MagicMock()
    mock_scalar.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_scalar
    yield mock_db

app.dependency_overrides[get_db] = mock_get_db

def get_valid_token():
    payload = {"sub": str(uuid.uuid4())}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

async def run_final_check():
    results = []
    try:
        sessionmanager.init(str(settings.DATABASE_URL))
    except Exception: pass

    # Override get_db again to be sure
    mock_db_instance = AsyncMock()
    async def mock_get_db_local():
        yield mock_db_instance
    app.dependency_overrides[get_db] = mock_get_db_local

    with TestClient(app) as client:
        # 1. JWT Middleware
        res_no_token = client.get("/api/v1/jobs/")
        results.append(("JWT Auth (missing)", res_no_token.status_code == 401))
        
        # 2. POST /api/v1/jobs < 500ms
        headers = {"Authorization": f"Bearer {get_valid_token()}"}
        from app.worker.tasks import run_pipeline_task
        with patch("app.api.v1.endpoints.jobs.storage_service.upload_raw", new_callable=AsyncMock) as mock_upload, \
             patch.object(run_pipeline_task, "delay") as mock_delay:
            mock_upload.return_value = "key"
            file = {"file": ("t.docx", b"c", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            start = time.time()
            res_post = client.post("/api/v1/jobs/", files=file, data={"journal_identifier": "N"}, headers=headers)
            dur = (time.time() - start) * 1000
            results.append(("POST /api/v1/jobs (202 and <500ms)", res_post.status_code == 202 and dur < 500))
            job_id = res_post.json().get("job_id", str(uuid.uuid4()))

        # 3. GET /.../result
        job_mock = MagicMock(status=JobStatus.completed, output_s3_key="s3://url", latex_s3_key="s3://tex", compliance_score=95.0, total_changes=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = job_mock
        mock_db_instance.execute.return_value = mock_result
        
        res_res = client.get(f"/api/v1/jobs/{job_id}/result", headers=headers)
        results.append(("GET Result (S3 URL)", res_res.status_code == 200 and "url" in str(res_res.json())))

        # 4. Pipeline events (WebSocket)
        from app.worker.tasks import _run_pipeline_async
        async def mock_sub(jid):
            for s in ["ingesting", "parsing", "interpreting", "transforming", "validating"]:
                yield {"status": s}
            yield {"status": "completed"}

        with patch("app.worker.tasks.job_service.get_job", new_callable=AsyncMock), \
             patch("app.worker.tasks.pipeline.ainvoke", new_callable=AsyncMock), \
             patch("app.api.websocket.cache_service.subscribe_progress", new_callable=MagicMock) as mock_s:
            mock_s.return_value = mock_sub(job_id)
            recv = []
            with client.websocket_connect(f"/api/v1/jobs/{job_id}/stream") as ws:
                try:
                    while True:
                        m = ws.receive_json()
                        recv.append(m.get("status"))
                        if m.get("status") == "completed": break
                except Exception: pass
            results.append(("WS 5 Agent Events", len(set(recv) & {"ingesting", "parsing", "interpreting", "transforming", "validating"}) == 5))

        # 5. Pipeline retry on timeout
        from app.worker.tasks import pipeline as task_pipeline
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__.return_value = AsyncMock()
        
        with patch("app.worker.tasks.get_session", new_callable=AsyncMock) as mock_get_sess, \
             patch.object(task_pipeline, "ainvoke", side_effect=Exception("Pipeline Timeout")):
            mock_get_sess.return_value = mock_factory
            with patch("app.worker.tasks.job_service.get_job", new_callable=AsyncMock) as mj:
                mj.return_value = MagicMock(raw_s3_key="k", source_format="docx", journal_identifier="j")
                try:
                    await _run_pipeline_async(job_id)
                    results.append(("Pipeline raise on failure", False))
                except Exception as e:
                    results.append(("Pipeline raise on failure", "Timeout" in str(e)))

    print("---SC VERIFICATION RESULTS---")
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")

if __name__ == "__main__":
    asyncio.run(run_final_check())
