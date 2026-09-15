import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "college_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def search(query, top_k=5):
    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(
        path=CHROMA_DIR
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    query_embedding = model.encode(
        [query]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )

    return results


if __name__ == "__main__":

    query = input("\nAsk a question: ")

    results = search(query)

    print("\nRelevant results:\n")

    for i, document in enumerate(
        results["documents"][0],
        start=1
    ):
        metadata = results["metadatas"][0][i - 1]

        print("=" * 70)

        print(f"Result {i}")
        print(f"File: {metadata['filename']}")
        print(f"Page: {metadata['page_number']}")
        print(f"Method: {metadata['method']}")

        print("\nText:")
        print(document)