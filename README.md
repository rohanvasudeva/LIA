# Lara Intelligent Assistant

LIA is a document-grounded chatbot for Vignan's Lara Institute of Technology &
Science. It retrieves relevant college-document excerpts from ChromaDB and uses
Groq to generate a sourced answer.

## Start LIA

1. Add the following values to `.env`:

   ```dotenv
   GROQ_API_KEY=your_key
   ADMIN_ID=admin
   ADMIN_PASSWORD=change-this-password
   ```

   The admin workspace is available from the first landing screen. Use the
   configured `ADMIN_ID` and `ADMIN_PASSWORD` to sign in.
2. From the project directory, run the same Docker command:

   ```powershell
   docker compose up --build
   ```

3. Open http://localhost:8000.

   If the image has already been rebuilt after these changes, `docker compose
   up` is sufficient. Use `docker compose up --build` whenever dependencies or
   backend code change.

For local development without Docker, activate `.venv` and run:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```

The compose setup hosts the interface and FastAPI service together on port
8000. It keeps the `chroma_db` vector store and uploaded PDFs on your machine,
so the container can reuse them on subsequent starts. Stop LIA with
`docker compose down`.

After an admin uploads a PDF, LIA automatically extracts its page text,
creates overlapping chunks, generates embeddings, and refreshes the Chroma
index before reporting the document as ready. Image-only/scanned PDFs are
handled through OCR as well.
