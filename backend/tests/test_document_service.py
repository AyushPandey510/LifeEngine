from app.services.document_service import (
    merge_document_signals,
    parse_uploaded_document,
)


def test_parse_resume_text_extracts_skills_and_sections():
    content = b"""
    Ayush Sharma
    Skills
    Python, FastAPI, React, PostgreSQL, Docker
    Experience
    Built a Future Self AI platform using FastAPI and React.
    Education
    B.Tech Computer Science
    """

    parsed = parse_uploaded_document("resume.txt", "text/plain", content)

    assert "python" in parsed.signals["skills"]
    assert "fastapi" in parsed.signals["skills"]
    assert parsed.signals["experience"]
    assert "Parsed resume.txt" in parsed.summary


def test_merge_document_signals_preserves_existing_profile_context():
    existing = {"communication_style": "direct"}
    signals = {"skills": ["python", "react"], "document_keywords": ["future", "platform"]}

    merged = merge_document_signals(existing, "resume", "resume.txt", signals)

    assert merged["communication_style"] == "direct"
    assert merged["document_profile"]["skills"] == ["python", "react"]
    assert merged["document_profile"]["uploads"][0]["filename"] == "resume.txt"


def test_pdf_upload_path_uses_pdf_reader(monkeypatch):
    class FakePage:
        def extract_text(self):
            return "Resume with Python FastAPI React certificate"

    class FakePdfReader:
        def __init__(self, stream):
            self.pages = [FakePage()]

    monkeypatch.setitem(
        __import__("sys").modules,
        "pypdf",
        type("FakePypdf", (), {"PdfReader": FakePdfReader}),
    )

    parsed = parse_uploaded_document("resume.pdf", "application/pdf", b"%PDF-1.4 fake")

    assert "python" in parsed.signals["skills"]
    assert "fastapi" in parsed.signals["skills"]
