# Lara Intelligent Assistant

LIA is a document-grounded chatbot for Vignan's Lara Institute of Technology &
Science. It retrieves relevant college-document excerpts from ChromaDB and uses
Groq to generate a sourced answer.

## Start LIA

1. Add `GROQ_API_KEY=your_key` to the existing `.env` file.
2. From the project directory, run:

   ```powershell
   docker compose up --build
   ```

3. Open http://localhost:8000.

The compose setup hosts the interface and FastAPI service together on port
8000. It keeps the existing `chroma_db` vector store on your machine, so the
container can reuse it on subsequent starts. Stop LIA with `docker compose down`.
