from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel

from services.pdf_service import extract_pdf_text, chunk_medical_text
from services.vector_service import create_faiss_index, search_context, save_index, load_index
from services.llm_service import generate_response, rewrite_query
from typing import List, Optional, Dict


app = FastAPI()

# -------------------------------
# CORS (for React frontend later)
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Global storage (MVP)
# -------------------------------
faiss_index = None
chunks_store = None

@app.on_event("startup")
async def startup_event():
    global faiss_index, chunks_store
    faiss_index, chunks_store = load_index()
    if faiss_index is None or chunks_store is None:
        print("No existing index found — waiting for PDF upload")
    else:
        print("FAISS index and chunks store loaded successfully")

class Message(BaseModel):
    role: str
    content: str

class AskRequest(BaseModel):
    pdf_id: str
    question: str
    history: Optional[List[Dict]] = None


def normalize_query_input(raw_query: str) -> str:
    """
    Unwrap accidentally nested JSON-string queries.
    Example:
      '{"query":"{\\"query\\":\\"...\\", \\"answer\\": ... }"}' -> "..."
    """
    query = (raw_query or "").strip()

    # Try a few rounds in case query was stringified multiple times.
    for _ in range(3):
        try:
            parsed = json.loads(query)
        except Exception:
            break

        if isinstance(parsed, dict):
            nested = parsed.get("query")
            if isinstance(nested, str):
                query = nested.strip()
                continue
        break

    return query


# -------------------------------
# 1. Health check
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/status")
def status():
    return {"has_index": faiss_index is not None and faiss_index.ntotal > 0}


# -------------------------------
# 2. Upload PDF
# -------------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global faiss_index, chunks_store

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Extract + chunk
        pages = extract_pdf_text(file_bytes)
        chunks = chunk_medical_text(pages)

        # Create FAISS index
        faiss_index, chunks_store = create_faiss_index(chunks)
        save_index(faiss_index, chunks_store)
    except ValueError as exc:
        # Extraction/chunking-level validation errors
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(exc)}",
        ) from exc

    return {
        "pdf_id": "default",
        "status": "success"
        
    }


# -------------------------------
# 3. Ask question
# -------------------------------
@app.post("/ask")
async def ask_question(payload: AskRequest):
    global faiss_index, chunks_store

    # 1. Validate system state
    if faiss_index is None:
        raise HTTPException(status_code=400, detail="No document uploaded yet")

    # 2. Extract inputs
    pdf_id = payload.pdf_id  # reserved for future multi-PDF support
    question = payload.question

    # 3. Normalize only for retrieval
    query = normalize_query_input(question)
    try :
        queries = rewrite_query(query)
        if not queries:
            queries = [query]
    except Exception:
        queries = [query]
        
    context, sources = search_context(queries, faiss_index, chunks_store or [])

    # 5. Generate answer using ORIGINAL question
    answer = generate_response(question, context, payload.history)

    # 6. Return structured response
    return {
        "answer": answer,
        "sources": sources
    }
