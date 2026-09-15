import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


CHUNKS_FILE = Path("data/chunks.json")
CHROMA_DIR = "chroma_db"

COLLECTION_NAME = "college_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def create_vector_store():
    if not CHUNKS_FILE.exists():
        print(f"Chunks file not found: {CHUNKS_FILE}")
        return

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("No chunks found.")
        return

    print(f"Loaded {len(chunks)} chunks.")

    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print("Connecting to ChromaDB...")

    client = chromadb.PersistentClient(
        path=CHROMA_DIR
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    # Clear existing data so re-running the script
    # doesn't create duplicate chunks.
    existing = collection.get()

    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        print("Cleared existing collection.")

    texts = []
    ids = []
    metadatas = []

    for chunk in chunks:
        texts.append(chunk["text"])

        ids.append(str(chunk["chunk_id"]))

        metadatas.append({
            "filename": chunk["filename"],
            "page_number": chunk["page_number"],
            "chunk_number": chunk["chunk_number"],
            "method": chunk["method"]
        })

    print("Generating embeddings...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True
    )

    print("Storing vectors in ChromaDB...")

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=metadatas
    )

    print("\nVector store created successfully.")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Documents: {collection.count()}")


if __name__ == "__main__":
    create_vector_store()