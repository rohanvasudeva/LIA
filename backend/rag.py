import os
import re
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

from backend.timetables import timetable_response

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = str(PROJECT_DIR / "chroma_db")
COLLECTION_NAME = "college_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

MODEL_NAME = "openai/gpt-oss-20b"

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR
)

collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
embedding_model = None
groq_client = None


def get_embedding_model():
    global embedding_model

    if embedding_model is None:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    return embedding_model


def get_groq_client():
    global groq_client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    if groq_client is None:
        groq_client = Groq(api_key=api_key)

    return groq_client


def _search_terms(question):
    terms = set(re.findall(r"[a-z0-9]+", question.lower()))

    if "4th" in terms or "fourth" in terms:
        terms.update({"iv", "fourth", "4th"})
    if "pe" in terms or "physical" in terms:
        terms.update({"pe", "physical"})
    if "teach" in terms or "teacher" in terms or "teaches" in terms:
        terms.update({"teach", "teacher", "teaches", "faculty"})

    return terms


def _lexical_score(text, terms):
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return sum(1 for term in terms if term in words)


def retrieve_context(question, top_k=8):
    """
    Retrieve the most relevant chunks from ChromaDB.
    """

    if collection.count() == 0:
        return []

    query_embedding = get_embedding_model().encode(
        [question]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count())
    )

    terms = _search_terms(question)
    all_chunks = collection.get(include=["documents", "metadatas"])
    lexical_matches = sorted(
        zip(all_chunks["documents"], all_chunks["metadatas"]),
        key=lambda item: _lexical_score(item[0], terms),
        reverse=True
    )

    candidates = []
    seen = set()
    for document, metadata in zip(
        results["documents"][0],
        results["metadatas"][0]
    ):
        key = document
        if key not in seen:
            candidates.append((document, metadata))
            seen.add(key)

    for document, metadata in lexical_matches[:top_k]:
        if _lexical_score(document, terms) == 0:
            break
        if document not in seen:
            candidates.append((document, metadata))
            seen.add(document)

    candidates.sort(
        key=lambda item: _lexical_score(item[0], terms),
        reverse=True
    )

    contexts = []

    for document, metadata in candidates[:top_k]:

        contexts.append({
            "text": document,
            "filename": metadata.get("filename", "Unknown file"),
            "page_number": metadata.get("page_number", "Unknown"),
            "method": metadata.get("method", "Unknown")
        })

    return contexts


def generate_answer(question, contexts):
    """
    Generate an answer using only retrieved college information.
    """

    context_text = ""

    for i, context in enumerate(contexts, start=1):

        context_text += (
            f"\n--- Source {i} ---\n"
            f"File: {context['filename']}\n"
            f"Page: {context['page_number']}\n"
            f"Content:\n{context['text']}\n"
        )

    prompt = f"""
You are a college AI assistant.

Answer the user's question using ONLY the information
provided in the context below.

Rules:
- Do not invent college-specific information.
- Do not use outside knowledge.
- If the answer cannot be found in the context, say:
  "I couldn't find this information in the available college documents."
- Keep the answer clear and concise.
- Do not mention the retrieval process.

Context:
{context_text}

User question:
{question}
"""

    response = get_groq_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a grounded college information assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    answer = response.choices[0].message.content

    return answer


def ask_question(question):
    """
    Complete RAG pipeline.
    """

    direct_answer = timetable_response(question)
    if direct_answer:
        return direct_answer

    contexts = retrieve_context(question)

    if not contexts:
        return {
            "answer": "I couldn't find any information in the available college documents.",
            "sources": []
        }

    answer = generate_answer(
        question,
        contexts
    )

    return {"answer": answer}