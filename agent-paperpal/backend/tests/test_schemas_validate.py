import uuid
from datetime import datetime
from app.schemas.job import JobCreate, JobResponse, JobStatusResponse
from app.schemas.result import ResultResponse, DiffResponse
from app.schemas.style import StyleListItem, JROPreviewResponse
from app.schemas.ir_schema import Author, Paragraph, IRSchema
from app.schemas.jro_schema import JROSchema
from app.schemas.validation_schema import JobState
from app.models.job import JobStatus


def test_schema_validations():
    # 1. JobCreate
    j_c = JobCreate(journal_identifier="IEEE", style_name="IEEE", force_refresh=True)
    assert j_c.journal_identifier == "IEEE"

    # 2. JobResponse
    j_r = JobResponse.model_validate({
        "id": str(uuid.uuid4()),
        "status": JobStatus.queued,
        "progress_pct": 50.5,
        "created_at": datetime.utcnow().isoformat(),
        "source_format": "docx"
    })
    assert j_r.status == JobStatus.queued

    # 3. ResultResponse
    r_r = ResultResponse.model_validate({
        "job_id": str(uuid.uuid4()),
        "docx_url": "s3://foo",
        "latex_url": "s3://bar",
        "compliance_score": 95.0,
        "total_changes": 10
    })
    assert r_r.docx_url == "s3://foo"

    # 4. IRSchema (nested testing)
    ir = IRSchema.model_validate({
        "job_id": "job_123",
        "source_format": "docx",
        "title": "A Review",
        "paragraphs": [{"id": "p1", "raw_text": "Hello world", "confidence": 0.99}],
        "metadata": {"word_count": 2}
    })
    assert len(ir.paragraphs) == 1
    assert ir.metadata.word_count == 2
    
    # 5. JROSchema
    jro = JROSchema.model_validate({
        "journal_name": "IEEE",
        "heading_rules": {"numbering_scheme": "arabic"},
        "abstract_rules": {"required_sections": []},
        "layout_rules": {"columns": 2},
        "figure_rules": {},
        "table_rules": {},
        "section_requirements": {},
        "extraction_source": "web",
        "extraction_confidence": 0.9
    })
    assert jro.layout_rules.columns == 2

    # 6. JobState typed dict setup
    state: JobState = {
        "job_id": "job_123",
        "raw_ir": ir,
        "annotated_ir": None,
        "jro": jro,
        "transformed_ir": None,
        "change_log": [],
        "compliance_report": None,
        "output_s3_urls": {},
        "status": JobStatus.completed,
        "errors": [],
        "progress_pct": 100.0,
    }
    assert state["status"] == JobStatus.completed

    print("All Pydantic models validated successfully.")
