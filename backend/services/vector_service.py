import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple


# -------------------------------
# 1. Load embedding model (global)
# -------------------------------
model = SentenceTransformer("intfloat/multilingual-e5-base")


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
def search_context(query: str, index, chunks: List[Dict], k: int = 3) -> Tuple[List[Dict], List[Dict]]:
    """
    Retrieve top-k relevant chunks using cosine similarity
    """
    """
    # Expand query
    expanded_query = expand_query(query)
    """

    if index is None or index.ntotal == 0:
        return [], []

    # Embed query
    query_vector = model.encode([query])
    query_vector = np.array(query_vector).astype("float32")

    # Normalize query vector
    faiss.normalize_L2(query_vector)

    # Search
    scores, indices = index.search(query_vector, k)

    SIMILARITY_THRESHOLD = 0.3  # tune this: raise if too much noise, lower if missing answers

    results = []
    for idx, score in zip(indices[0], scores[0]):
        if idx == -1:
            continue
        if score < SIMILARITY_THRESHOLD:  # skip low-relevance chunks
            continue
        results.append({
            "text": chunks[idx]["text"],
            "page": chunks[idx]["page"],
            "score": float(score)
        })

    # Keep full results for prompt building, and lightweight sources for UI.
    sources = [{"text": item["text"], "page": item["page"]} for item in results]
    return results, sources