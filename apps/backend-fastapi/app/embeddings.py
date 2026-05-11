from sentence_transformers import SentenceTransformer
import numpy as np

_model: SentenceTransformer | None = None


def init_model(model_name: str = "all-MiniLM-L6-v2") -> None:
    global _model
    _model = SentenceTransformer(model_name)


def get_embedding(text: str) -> list[float]:
    vector = _model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    vectors = _model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]


def embedding_to_pg_str(embedding: list[float]) -> str:
    """Convierte embedding a string compatible con pgvector."""
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
