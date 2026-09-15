import json
from pathlib import Path


INPUT_FILE = Path("data/extracted_text.json")
OUTPUT_FILE = Path("data/chunks.json")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split text into overlapping chunks.
    """

    text = " ".join(text.split())

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def create_chunks():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)

    all_chunks = []
    chunk_id = 0

    for document in documents:
        filename = document["filename"]

        for page in document["pages"]:
            page_number = page["page_number"]
            text = page["text"]
            method = page["method"]

            chunks = split_text(text)

            for chunk_number, chunk in enumerate(chunks, start=1):
                chunk_id += 1

                all_chunks.append({
                    "chunk_id": chunk_id,
                    "filename": filename,
                    "page_number": page_number,
                    "chunk_number": chunk_number,
                    "method": method,
                    "text": chunk
                })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            all_chunks,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Created {len(all_chunks)} chunks.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    create_chunks()