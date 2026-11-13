"""
tests/test_parser.py – Unit Tests for Resume Parser and Text Normalization.
"""

import pytest
from pathlib import Path
from backend.resume_parser import normalize_text, parse_resume_document


def test_normalize_text_characters():
    raw = "Senior\u00a0Software  Engineer\n• Built Python\u2013Django microservices\n\u2018Impact\u2019: 40% reduction"
    cleaned = normalize_text(raw)
    assert "\u00a0" not in cleaned
    assert "•" in cleaned
    assert "Senior Software Engineer" in cleaned
    assert "'Impact': 40% reduction" in cleaned


def test_unsupported_format_raises_error(tmp_path):
    test_file = tmp_path / "resume.xyz"
    test_file.write_text("dummy resume text")
    with pytest.raises(ValueError, match="Unsupported file format"):
        parse_resume_document(test_file, "resume.xyz")


def test_empty_document_raises_error(tmp_path):
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")
    with pytest.raises(ValueError):
        parse_resume_document(empty_pdf, "empty.pdf")
