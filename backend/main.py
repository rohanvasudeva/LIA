import hmac
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.document_pipeline import ingest_all_documents, list_documents, save_uploaded_pdf
from backend.rag import ask_question

load_dotenv()


app = FastAPI(
    title="Lara Intelligent Assistant",
    description="Prototype AI assistant grounded in college documents"
)

ADMIN_ID = os.getenv("ADMIN_ID", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "lia-admin")
admin_tokens = set()


class ChatRequest(BaseModel):
    question: str


class AdminLogin(BaseModel):
    admin_id: str
    password: str


def require_admin(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin login required.")
    token = authorization.removeprefix("Bearer ").strip()
    if token not in admin_tokens:
        raise HTTPException(status_code=401, detail="Admin session expired.")
    return token


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


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.post("/chat")
def chat(request: ChatRequest):
    question = request.question.strip()

    if not question:
        return {"answer": "Please enter a question."}

    result = ask_question(question)

    return result


@app.post("/admin/login")
def admin_login(request: AdminLogin):
    valid_id = hmac.compare_digest(request.admin_id, ADMIN_ID)
    valid_password = hmac.compare_digest(request.password, ADMIN_PASSWORD)
    if not (valid_id and valid_password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")
    token = secrets.token_urlsafe(32)
    admin_tokens.add(token)
    return {"token": token}


@app.get("/admin/documents")
def admin_documents(_: str = Depends(require_admin)):
    return {"documents": list_documents()}


@app.post("/admin/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    _: str = Depends(require_admin),
):
    filename = file.filename or ""
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDFs must be smaller than 25 MB.")

    filename = save_uploaded_pdf(filename, content)
    try:
        stats = ingest_all_documents()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {exc}") from exc
    return {"filename": filename, **stats}


@app.post("/admin/documents/reindex")
def reindex_documents(_: str = Depends(require_admin)):
    try:
        return ingest_all_documents()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reindex failed: {exc}") from exc


app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
    name="frontend"
)
