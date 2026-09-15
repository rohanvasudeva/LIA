from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.rag import ask_question


app = FastAPI(
    title="Lara Intelligent Assistant",
    description="Prototype AI assistant grounded in college documents"
)


class ChatRequest(BaseModel):
    question: str


@app.get("/api")
def api_root():
    return {
        "message": "College AI Assistant API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    question = request.question.strip()

    if not question:
        return {
            "answer": "Please enter a question.",
            "sources": []
        }

    result = ask_question(question)

    return result


app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
    name="frontend"
)
