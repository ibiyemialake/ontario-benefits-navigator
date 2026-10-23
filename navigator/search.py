"""RAG layer over official pages. Multilingual embeddings so French questions
find French content (Chroma's default model is English-only)."""
from pathlib import Path

INDEX_DIR = Path(__file__).parent.parent / "index"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_col = None


def get_collection(reset: bool = False):
    global _col
    import chromadb
    from chromadb.utils import embedding_functions

    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    if reset:
        try:
            client.delete_collection("sources")
        except Exception:
            pass
    embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    _col = client.get_or_create_collection("sources", embedding_function=embed,
                                           metadata={"hnsw:space": "cosine"})
    return _col


def search(query: str, lang: str, k: int = 5) -> list[dict]:
    col = _col or get_collection()
    res = col.query(query_texts=[query], n_results=k, where={"lang": lang})
    return [{"chunk_id": i, "program_id": m["program_id"], "url": m["url"],
             "fetched": m["fetched"], "text": d}
            for i, m, d in zip(res["ids"][0], res["metadatas"][0], res["documents"][0])]


def get_chunks(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    col = _col or get_collection()
    res = col.get(ids=ids)
    return {i: {"text": d, **m} for i, d, m in zip(res["ids"], res["documents"], res["metadatas"])}
