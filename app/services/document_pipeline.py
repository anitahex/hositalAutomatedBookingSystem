from __future__ import annotations

import base64
import io
import re
from typing import Any

from fastapi import HTTPException, UploadFile

try:  # optional
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover
    Image = None

try:  # optional
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover
    PdfReader = None

try:  # optional
    import fitz  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    fitz = None

try:  # optional
    import pdfplumber  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    pdfplumber = None

try:  # optional
    from pdf2image import convert_from_bytes  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    convert_from_bytes = None


ALLOWED_UPLOAD_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}

# How many pages of a PDF are read for text. Previously an unnamed `[:12]` repeated in
# three reader branches. Named because it is a real limit with a real consequence: a
# discharge summary longer than this has no extracted text beyond page 12, so nothing
# there can be summarised or cited. Raising it is a cost/latency decision, not a typo fix.
PDF_TEXT_PAGE_LIMIT = 12

MEDICAL_KEYWORDS = (
    "medical",
    "report",
    "prescription",
    "lab",
    "scan",
    "xray",
    "x-ray",
    "mri",
    "ct",
    "ultrasound",
    "pathology",
    "doctor",
    "hospital",
    "clinic",
    "symptom",
    "diagnosis",
    "blood",
    "test",
    "result",
    "patient",
    "radiology",
)


def _normalized_text(*parts: str | None) -> str:
    return " ".join(str(part or "").lower().replace("-", " ").replace("_", " ").split())


def _looks_medical(filename: str, extracted_text: str) -> bool:
    sample = _normalized_text(filename, extracted_text)
    if not sample:
        return False
    return any(keyword in sample for keyword in MEDICAL_KEYWORDS)


def _to_data_url(mime_type: str, data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def extract_pdf_pages(upload_bytes: bytes) -> list[dict]:
    """Per-page text: [{"page_no": 1, "text": "..."}, ...], 1-indexed.

    Same three-library fallback chain and same page cap as _extract_pdf_text, which is now
    a thin join over this — the loops already walked pages one at a time and threw the
    page numbers away at the end.

    Page numbers are needed because a grounded summary has to quote a specific page and
    stay verifiable against it later. A flattened blob of text cannot support "this
    sentence came from page 2", and cannot be re-checked once the file is only in storage.

    Pages that yield no text are omitted rather than stored empty: an image-only page has
    no text layer, and recording "" for it would make a scanned document look like a
    document whose pages are genuinely blank.
    """
    pages: list[dict] = []

    def _collect(reader):
        """reader yields (page_no, text). Returns pages that actually had text."""
        out = []
        for page_no, text in reader():
            text = (text or "").strip()
            if text:
                out.append({"page_no": page_no, "text": text})
        return out

    def _pypdf():
        reader = PdfReader(io.BytesIO(upload_bytes))
        for index, page in enumerate(reader.pages[:PDF_TEXT_PAGE_LIMIT], start=1):
            yield index, page.extract_text()

    def _pdfplumber():
        with pdfplumber.open(io.BytesIO(upload_bytes)) as pdf:  # type: ignore[arg-type]
            for index, page in enumerate(pdf.pages[:PDF_TEXT_PAGE_LIMIT], start=1):
                yield index, page.extract_text()

    def _fitz():
        doc = fitz.open(stream=upload_bytes, filetype="pdf")  # type: ignore[attr-defined]
        for index, page in enumerate(doc[:PDF_TEXT_PAGE_LIMIT], start=1):
            yield index, page.get_text("text")

    for available, reader in (
        (PdfReader is not None, _pypdf),
        (pdfplumber is not None, _pdfplumber),
        (fitz is not None, _fitz),
    ):
        if not available or pages:
            continue
        try:
            pages = _collect(reader)
        except Exception:
            pages = []

    return pages


def _extract_pdf_text(upload_bytes: bytes) -> str:
    """Unchanged contract: the whole document as one string, pages separated by a blank
    line. Several call sites want exactly that. It is now expressed in terms of
    extract_pdf_pages so the two can never disagree about what a document says."""
    return "\n\n".join(page["text"] for page in extract_pdf_pages(upload_bytes)).strip()


def _extract_pdf_images(upload_bytes: bytes) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []

    if convert_from_bytes is not None:
        try:
            pages = convert_from_bytes(upload_bytes, dpi=150, first_page=1, last_page=3)
            for page in pages:
                buffer = io.BytesIO()
                page.convert("RGB").save(buffer, format="JPEG", quality=82)
                images.append({
                    "mime_type": "image/jpeg",
                    "data_url": _to_data_url("image/jpeg", buffer.getvalue()),
                })
        except Exception:
            images = []

    if not images and fitz is not None:
        try:
            doc = fitz.open(stream=upload_bytes, filetype="pdf")  # type: ignore[attr-defined]
            for page in doc[:3]:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)  # type: ignore[attr-defined]
                images.append({
                    "mime_type": "image/jpeg",
                    "data_url": _to_data_url("image/jpeg", pix.tobytes("jpeg")),
                })
        except Exception:
            images = []

    return images


def _extract_image(upload_bytes: bytes, mime_type: str) -> list[dict[str, str]]:
    if Image is None:
        encoded = _to_data_url(mime_type or "image/jpeg", upload_bytes)
        return [{
            "mime_type": mime_type or "image/jpeg",
            "data_url": encoded,
        }]

    try:
        image = Image.open(io.BytesIO(upload_bytes))
        rgb_image = image.convert("RGB")
        buffer = io.BytesIO()
        rgb_image.save(buffer, format="JPEG", quality=85)
        return [{
            "mime_type": "image/jpeg",
            "data_url": _to_data_url("image/jpeg", buffer.getvalue()),
        }]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded image: {exc}") from exc


def extract_uploaded_document(upload: UploadFile) -> dict[str, Any]:
    filename = upload.filename or "uploaded-file"
    mime_type = upload.content_type or "application/octet-stream"

    if mime_type not in ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and JPEG/PNG uploads are supported.")

    upload_bytes = upload.file.read()
    if not upload_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(upload_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Uploaded file is too large.")

    text = ""
    images: list[dict[str, str]] = []
    page_count = 0

    if mime_type == "application/pdf":
        text = _extract_pdf_text(upload_bytes)
        images = _extract_pdf_images(upload_bytes)
        page_count = len(images) or max(1, text.count("\f") + 1 if text else 1)
        # Keyword check only for PDFs where we have extractable text to evaluate
        if text and not _looks_medical(filename, text):
            raise HTTPException(
                status_code=400,
                detail="Please upload a medical document such as a report, prescription, lab result, or scan.",
            )
    else:
        # Images: no text to check — medical relevance is verified by Azure GPT-4o in /chat/upload
        images = _extract_image(upload_bytes, mime_type)
        page_count = 1

    return {
        "file_name": filename,
        "mime_type": mime_type,
        "text": text,
        "images": images,
        "page_count": page_count,
        "source": "pdf" if mime_type == "application/pdf" else "image",
    }
