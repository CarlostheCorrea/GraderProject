from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx"}


def _normalize_basic_whitespace(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")


def _looks_fragmented(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    short_lines = sum(1 for line in lines if len(line) <= 22)
    return (short_lines / len(lines)) >= 0.45


def _normalize_pdf_text(text: str) -> str:
    text = _normalize_basic_whitespace(text)
    text = re.sub(r"[ \t]+", " ", text)

    # Keep paragraph breaks when available, but normalize internal spacing.
    blocks = [block.strip() for block in re.split(r"\n{2,}", text) if block.strip()]
    normalized_blocks = [re.sub(r"\s+", " ", block).strip() for block in blocks]
    normalized = "\n\n".join(block for block in normalized_blocks if block)

    # Some PDFs extract with a newline every word; flatten aggressively in that case.
    if _looks_fragmented(normalized):
        normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized.strip()


def _extract_pdf(raw: bytes) -> str:
    reader = PdfReader(BytesIO(raw))
    page_text: list[str] = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    joined = "\n\n".join(chunk.strip() for chunk in page_text if chunk.strip())
    return _normalize_pdf_text(joined)


def _extract_txt(raw: bytes) -> str:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        decoded = raw.decode("latin-1", errors="ignore")
    return _normalize_basic_whitespace(decoded).strip()


def _extract_docx(raw: bytes) -> str:
    document = Document(BytesIO(raw))
    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    return _normalize_basic_whitespace(text).strip()


def extract_text_from_file(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf(raw)
    elif suffix == ".txt":
        text = _extract_txt(raw)
    elif suffix == ".docx":
        text = _extract_docx(raw)
    elif suffix == ".doc":
        raise ValueError("Legacy .doc files are not supported. Please convert to .docx and re-upload.")
    else:
        raise ValueError("Unsupported file type. Please upload a PDF, TXT, or DOCX file.")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("No readable text found in uploaded file.")
    return cleaned
