import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, Optional
import os
import json
from pathlib import Path


STORAGE_DIR = Path(os.getenv("RAG_STORAGE_PATH", "storage"))
INDEX_PATH  = STORAGE_DIR / "index.faiss"
CHUNKS_PATH = STORAGE_DIR / "chunks.json"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def save_index(index: faiss.Index, chunks: List[Dict]):
    faiss.write_index(index, str(INDEX_PATH))
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

def load_index() -> Tuple[Optional[faiss.Index], Optional[List[Dict]]]:
    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    else:
        return (None, None)
    return index, chunks

# -------------------------------
# 1. Load embedding model (global)
# -------------------------------
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


# -------------------------------
# 2. Create FAISS index (COSINE)
# -------------------------------
def create_faiss_index(chunks: List[Dict]):
    """
    Creates FAISS index using cosine similarity
    Returns: index, chunks
    """

    texts = [chunk["text"] for chunk in chunks]

    # Generate embeddings
    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    # 🔥 Normalize embeddings (required for cosine)
    faiss.normalize_L2(embeddings)

    # Use Inner Product (cosine after normalization)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    return index, chunks

"""
# -------------------------------
# 3. Medical query expansion
# -------------------------------
def expand_query(query: str) -> str:

    Expand query with medical synonyms (Arabic + French + English)

    expansions = {
        "قلب": "cardiaque heart cardio",
        "ذبحة": "angine infarctus chest pain",
        "ضغط": "hypertension tension artérielle",
        "نبض": "rythme cardiaque heartbeat pulse",
    }

    expanded_query = query

    for key, value in expansions.items():
        if key in query:
            expanded_query += " " + value

    return expanded_query

"""
# -------------------------------
# 4. Search context
# -------------------------------
def search_context(queries: List[str], index, chunks: List[Dict], k: int = 3) -> Tuple[List[Dict], List[Dict]]:
    """
    Retrieve top-k relevant chunks using cosine similarity across multiple queries.
    """

    if index is None or index.ntotal == 0:
        return [], []

    SIMILARITY_THRESHOLD = 0.3
    merged_results = {}

    for query in queries:
        query_vector = model.encode([query])
        query_vector = np.array(query_vector).astype("float32")
        faiss.normalize_L2(query_vector)

        scores, indices = index.search(query_vector, k)

        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:
                continue
            if score < SIMILARITY_THRESHOLD:
                continue
            if idx not in merged_results or score > merged_results[idx]:
                merged_results[idx] = score

    final = sorted(merged_results.items(), key=lambda x: x[1], reverse=True)

    results = [{"text": chunks[idx]["text"], "page": chunks[idx]["page"], "score": score} for idx, score in final]
    sources = [{"text": chunks[idx]["text"], "page": chunks[idx]["page"]} for idx, score in final]

    return results, sources
