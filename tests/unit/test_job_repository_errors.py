"""Job repository: per-format failure messages + cover audit survive persistence.

The Khởi-Nguồn defect (2026-08-24): a docx+pdf job whose PDF failed reported
"complete" with the PDF silently missing, and nothing recorded which cover the
caller asked for. Both facts are now columns.
"""

from api.job_repository import JobRepository


def _repo(tmp_path):
    return JobRepository(db_path=str(tmp_path / "jobs.db"))


def _job(job_id="j1", **over):
    base = {
        "job_id": job_id,
        "source_file": "book.pdf",
        "source_language": "vi",
        "target_language": "en",
        "profile_id": "novel",
        "output_formats": ["docx", "pdf"],
        "status": "running",
        "output_paths": {},
        "content_path": "uploads/v2/x.txt",
        "cover_template": "noir",
        "cover_image": "",
    }
    base.update(over)
    return base


def test_cover_request_is_persisted(tmp_path):
    repo = _repo(tmp_path)
    repo.save(_job())
    loaded = repo.get("j1")
    assert loaded["cover_template"] == "noir"
    assert loaded["cover_image"] == ""


def test_mark_complete_records_per_format_errors(tmp_path):
    repo = _repo(tmp_path)
    repo.save(_job())
    repo.mark_complete(
        "j1",
        {"docx": "outputs/v2/j1.docx"},
        {"pdf": "xelatex not found"},
    )
    loaded = repo.get("j1")
    assert loaded["status"] == "complete"
    assert loaded["output_paths"] == {"docx": "outputs/v2/j1.docx"}
    assert loaded["output_errors"] == {"pdf": "xelatex not found"}


def test_mark_complete_without_errors_keeps_empty_dict(tmp_path):
    repo = _repo(tmp_path)
    repo.save(_job(job_id="j2"))
    repo.mark_complete("j2", {"docx": "o.docx"})
    assert repo.get("j2")["output_errors"] == {}
