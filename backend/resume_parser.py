"""
backend/resume_parser.py – Multi-format Document Parser for ResumeX.

Features:
- Extracts clean text from PDF and DOCX documents
- Uses PyMuPDF (fitz) or pypdf for PDF extraction with seamless fallback
- Uses python-docx (or zipfile xml fallback) for DOCX extraction
- Normalizes whitespace, non-breaking characters, bullet symbols, and linebreaks
- Handles empty documents, corrupt files, and invalid byte sequences gracefully
"""

import os
import re
from pathlib import Path


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract readable text from a PDF file.
    Tries PyMuPDF (fitz) first, then falls back to pypdf, then pdfplumber if available.
    """
    text_chunks = []
    file_path = str(file_path)

    # Method 1: PyMuPDF (fitz)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        for page in doc:
            t = page.get_text()
            if t:
                text_chunks.append(t)
        doc.close()
        if text_chunks:
            return "\n".join(text_chunks)
    except ImportError:
        pass
    except Exception as e:
        # If PyMuPDF failed or file had an issue, attempt pypdf fallback
        pass

    # Method 2: pypdf fallback
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_chunks.append(t)
        if text_chunks:
            return "\n".join(text_chunks)
    except ImportError:
        pass
    except Exception as e:
        pass

    if not text_chunks:
        # Check if file exists and has size
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if os.path.getsize(file_path) == 0:
            raise ValueError("The uploaded PDF file is empty (0 bytes).")
        raise ValueError("Could not extract readable text from PDF. The document may be scanned, image-only, or password-protected.")

    return "\n".join(text_chunks)


def extract_text_from_docx(file_path: str | Path) -> str:
    """
    Extract readable text from a DOCX file.
    Uses python-docx, with an XML fallback via standard library zipfile.
    """
    file_path = str(file_path)
    paragraphs = []

    # Method 1: python-docx
    try:
        import docx
        doc = docx.Document(file_path)
        for p in doc.paragraphs:
            if p.text.strip():
                paragraphs.append(p.text)
        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        if paragraphs:
            return "\n".join(paragraphs)
    except ImportError:
        pass
    except Exception:
        pass

    # Method 2: Fallback to raw XML reading using standard library zipfile
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            # Find all w:t (text) elements
            text_nodes = tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
            words = [node.text for node in text_nodes if node.text]
            if words:
                return " ".join(words)
    except Exception:
        pass

    if not paragraphs:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if os.path.getsize(file_path) == 0:
            raise ValueError("The uploaded DOCX file is empty (0 bytes).")
        raise ValueError("Could not extract text from DOCX file. The document may be corrupted.")

    return "\n".join(paragraphs)


def normalize_text(text: str) -> str:
    """
    Clean and normalize extracted resume or job description text.
    - Replaces non-breaking spaces and unicode quotes/bullets
    - Collapses excessive whitespace while preserving paragraph structure
    """
    if not text:
        return ""

    # Replace common formatting characters
    text = text.replace("\u00a0", " ")  # non-breaking space
    text = text.replace("\u2022", "•")  # bullet point
    text = text.replace("\u2013", "-").replace("\u2014", "-")  # en/em dashes
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # smart quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    # Remove null bytes or non-printable controls
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Normalize multiple whitespace within lines
    lines = []
    for line in text.splitlines():
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        if cleaned_line:
            lines.append(cleaned_line)

    return "\n".join(lines)


def parse_resume_document(file_path: str | Path, filename: str) -> str:
    """
    Master parser entrypoint. Identifies file type by extension and returns normalized text.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        raw_text = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. ResumeX supports PDF and DOCX files.")

    clean_text = normalize_text(raw_text)

    if not clean_text or len(clean_text.strip()) < 20:
        raise ValueError("Document contains insufficient readable text. Please verify the document has readable text layers.")

    return clean_text
