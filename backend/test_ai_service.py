# test_ai_service.py
import asyncio
from unittest.mock import MagicMock
from app.services.ai_service import _score_relevance, _build_document_context

# --- Mock a UserDocument ---
def make_doc(doc_type, filename, skills, keywords, text):
    doc = MagicMock()
    doc.document_type = doc_type
    doc.filename = filename
    doc.extracted_text = text
    doc.extracted_signals = {
        "skills": skills,
        "document_keywords": keywords,
        "experience": ["Built REST APIs at Acme Corp", "Led backend team of 4"],
        "education": ["B.Tech Computer Science, 2021"],
        "certifications": [],
        "projects": ["AI chatbot using FastAPI and Groq"],
    }
    return doc

resume = make_doc(
    "resume", "my_resume.pdf",
    skills=["python", "fastapi", "postgresql", "docker"],
    keywords=["backend", "api", "microservices"],
    text="Experienced backend engineer with 3 years in Python and FastAPI..."
)

docs = [resume]

# --- Test relevance scoring ---
print("=== Relevance Scores ===")
queries = [
    "What are my skills?",           # should be HIGH
    "Tell me about my experience",   # should be HIGH
    "What is the weather today?",    # should be LOW / zero
    "Tell me a joke",                # should be ZERO
    "Do I know Python?",             # should be HIGH
    "Write me a cover letter",       # should be MEDIUM
]

for q in queries:
    score = _score_relevance(q, resume)
    print(f"  [{score:.2f}] {q}")

# --- Test context building ---
print("\n=== Context Injection ===")
for q in queries:
    ctx = _build_document_context(q, docs, threshold=0.15)
    injected = bool(ctx)
    print(f"  {'✅ injected' if injected else '❌ skipped '} → {q}")