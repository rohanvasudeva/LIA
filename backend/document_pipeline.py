import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import pymupdf
import pytesseract
from PIL import Image

from backend.rag import CHROMA_DIR, COLLECTION_NAME, get_embedding_model


PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_DIR / "data" / "pdfs"
EXTRACTED_FILE = PROJECT_DIR / "data" / "extracted_text.json"
CHUNKS_FILE = PROJECT_DIR / "data" / "chunks.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_text(text: str) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def _safe_filename(filename: str) -> str:
    cleaned = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", cleaned).strip(" .")
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned or "document.pdf"


def _extract_page_text(page):
    text = page.get_text("text").strip()
    if text:
        return text, "text"

    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    text = pytesseract.image_to_string(image).strip()
    return text, "ocr"


def extract_documents() -> list[dict]:
    documents = []
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        pages = []
        with pymupdf.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text, method = _extract_page_text(page)
                pages.append({
                    "page_number": page_number,
                    "text": text,
                    "method": method,
                })
            page_count = len(pdf)

        documents.append({
            "filename": pdf_path.name,
            "page_count": page_count,
            "text_pages": sum(page["method"] == "text" for page in pages),
            "ocr_pages": sum(page["method"] == "ocr" for page in pages),
            "empty_pages": sum(not page["text"] for page in pages),
            "pages": pages,
        })

    EXTRACTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    EXTRACTED_FILE.write_text(
        json.dumps(documents, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return documents


def build_chunks(documents: list[dict]) -> list[dict]:
    chunks = []
    for document in documents:
        for page in document["pages"]:
            for chunk_number, text in enumerate(split_text(page["text"]), start=1):
                identity = (
                    f'{document["filename"]}:{page["page_number"]}:{chunk_number}:{text}'
                )
                chunks.append({
                    "chunk_id": hashlib.sha1(identity.encode("utf-8")).hexdigest(),
                    "filename": document["filename"],
                    "page_number": page["page_number"],
                    "chunk_number": chunk_number,
                    "method": page["method"],
                    "text": text,
                })

    CHUNKS_FILE.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return chunks


def rebuild_vector_store(chunks: list[dict]) -> int:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    if chunks:
        texts = [chunk["text"] for chunk in chunks]
        embeddings = get_embedding_model().encode(texts).tolist()
        collection.add(
            ids=[chunk["chunk_id"] for chunk in chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "filename": chunk["filename"],
                    "page_number": chunk["page_number"],
                    "chunk_number": chunk["chunk_number"],
                    "method": chunk["method"],
                }
                for chunk in chunks
            ],
        )
    return len(chunks)


def ingest_all_documents() -> dict:
    documents = extract_documents()
    chunks = build_chunks(documents)
    chunk_count = rebuild_vector_store(chunks)
    return {
        "documents": len(documents),
        "chunks": chunk_count,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def list_documents() -> list[dict]:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    chunks_by_file = {}
    if CHUNKS_FILE.exists():
        chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
        for chunk in chunks:
            chunks_by_file[chunk["filename"]] = chunks_by_file.get(chunk["filename"], 0) + 1

    return [
        {
            "filename": path.name,
            "size": path.stat().st_size,
            "chunks": chunks_by_file.get(path.name, 0),
            "updated_at": datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }
        for path in sorted(PDF_DIR.glob("*.pdf"))
    ]


def save_uploaded_pdf(filename: str, content) -> str:
    safe_name = _safe_filename(filename)
    destination = PDF_DIR / safe_name
    destination.write_bytes(content)
    return safe_name
