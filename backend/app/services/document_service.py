"""
Document parsing and profile-signal extraction.

The upload flow stores parsed text and derived signals, not the raw file.
This keeps the personalization useful while reducing sensitive file storage.
"""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import json
import re
import zipfile
import xml.etree.ElementTree as ET


MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_STORED_TEXT_CHARS = 20000
SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".docx", ".pdf"}
ALLOWED_DOCUMENT_TYPES = {"resume", "cover_letter", "certificate", "other"}


@dataclass
class ParsedDocument:
    text: str
    signals: dict
    summary: str


def parse_uploaded_document(filename: str, content_type: str | None, content: bytes) -> ParsedDocument:
    """Parse an uploaded user document and extract profile signals."""
    if not content:
        raise ValueError("Uploaded file is empty.")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("File is too large. Upload a file under 5 MB.")

    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload .txt, .md, .json, .docx, or .pdf.")

    if extension in {".txt", ".md"}:
        text = _decode_text(content)
    elif extension == ".json":
        text = _parse_json(content)
    elif extension == ".docx":
        text = _parse_docx(content)
    elif extension == ".pdf":
        text = _parse_pdf(content)
    else:
        text = ""

    text = _normalize_text(text)
    if len(text) < 20:
        raise ValueError("Could not extract enough readable text from this document.")

    stored_text = text[:MAX_STORED_TEXT_CHARS]
    signals = extract_document_signals(stored_text)
    return ParsedDocument(
        text=stored_text,
        signals=signals,
        summary=_build_summary(filename, signals, stored_text),
    )


def extract_document_signals(text: str) -> dict:
    """Heuristic signal extraction for resumes, cover letters, and certificates."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    compact = " ".join(lines)

    signals = {
        "skills": _extract_skills(compact),
        "emails": _unique(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", compact))[:3],
        "phones": _unique(re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", compact))[:3],
        "links": _unique(re.findall(r"https?://[^\s,)]+|(?:github|linkedin)\.com/[^\s,)]+", compact, re.I))[:8],
        "education": _extract_section(lines, ("education", "academic", "qualification"), stop_words=("experience", "skills", "projects", "certifications")),
        "experience": _extract_section(lines, ("experience", "work experience", "employment"), stop_words=("education", "skills", "projects", "certifications")),
        "projects": _extract_section(lines, ("projects", "project"), stop_words=("education", "experience", "skills", "certifications")),
        "certifications": _extract_section(lines, ("certifications", "certificates", "licenses"), stop_words=("education", "experience", "skills", "projects")),
        "document_keywords": _extract_keywords(compact),
    }
    return {key: value for key, value in signals.items() if value}


def merge_document_signals(existing: dict, document_type: str, filename: str, signals: dict) -> dict:
    """Merge document-derived signals into profile.personality."""
    personality = dict(existing or {})
    document_profile = dict(personality.get("document_profile") or {})

    for key in ("skills", "links", "education", "experience", "projects", "certifications", "document_keywords"):
        merged = list(document_profile.get(key) or [])
        for item in signals.get(key, []):
            if item not in merged:
                merged.append(item)
        document_profile[key] = merged[:30]

    uploads = list(document_profile.get("uploads") or [])
    uploads.append({"type": document_type, "filename": filename})
    document_profile["uploads"] = uploads[-20:]

    personality["document_profile"] = document_profile
    return personality


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _parse_json(content: bytes) -> str:
    data = json.loads(_decode_text(content))
    return json.dumps(data, indent=2, ensure_ascii=False)


def _parse_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            xml_content = archive.read("word/document.xml")
    except Exception as exc:
        raise ValueError("Could not read this .docx file.") from exc

    root = ET.fromstring(xml_content)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        paragraph_text = "".join(text_parts).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)
    return "\n".join(paragraphs)


def _parse_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:
            raise ValueError("PDF parsing needs the 'pypdf' package. Run `pip install -r requirements.txt` and restart the backend.") from exc

    try:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError("Could not extract readable text from this PDF.") from exc


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_skills(text: str) -> list[str]:
    known_skills = [
        "python", "javascript", "typescript", "react", "fastapi", "django", "flask",
        "node.js", "postgresql", "mysql", "redis", "docker", "kubernetes", "aws",
        "gcp", "azure", "machine learning", "deep learning", "nlp", "llm", "sql",
        "data analysis", "pandas", "numpy", "tensorflow", "pytorch", "git",
        "linux", "rest api", "graphql", "tailwind", "figma",
    ]
    lowered = text.lower()
    return [skill for skill in known_skills if skill in lowered][:25]


def _extract_section(lines: list[str], headers: tuple[str, ...], stop_words: tuple[str, ...]) -> list[str]:
    results = []
    collecting = False
    for line in lines:
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        is_header = any(normalized == header or normalized.startswith(f"{header} ") for header in headers)
        if is_header:
            collecting = True
            continue
        if collecting and any(normalized == word or normalized.startswith(f"{word} ") for word in stop_words):
            break
        if collecting and 3 <= len(line) <= 180:
            results.append(line)
        if len(results) >= 8:
            break
    return results


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", text.lower())
    stop_words = {
        "the", "and", "for", "with", "from", "this", "that", "you", "your", "resume",
        "cover", "letter", "certificate", "email", "phone", "using", "built", "work",
    }
    counts = {}
    for word in words:
        if word not in stop_words:
            counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:15]]


def _build_summary(filename: str, signals: dict, text: str) -> str:
    pieces = [f"Parsed {filename} ({len(text)} chars)."]
    if signals.get("skills"):
        pieces.append(f"Skills: {', '.join(signals['skills'][:8])}.")
    if signals.get("certifications"):
        pieces.append(f"Certificates: {len(signals['certifications'])} signal(s).")
    if signals.get("experience"):
        pieces.append(f"Experience lines: {len(signals['experience'])}.")
    return " ".join(pieces)


def _unique(items: list[str]) -> list[str]:
    result = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result
