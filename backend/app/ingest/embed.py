"""Embedding providers (docs/adr/0006). `fake` is deterministic, for tests and CI."""

import hashlib
import math
from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder:
    """fastembed on ONNX Runtime. The model is pre-downloaded in the Docker image."""

    def __init__(self, model: str, dim: int) -> None:
        from fastembed import TextEmbedding

        self.dim = dim
        self._model = TextEmbedding(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts, batch_size=32)]


class FakeEmbedder:
    """Hashes words into a fixed-size unit vector: same text, same vector; shared words, nearby vectors."""

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dim
            for word in text.lower().split():
                h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
                vector[h % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            out.append([v / norm for v in vector])
        return out


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedding_provider == "fake":
        return FakeEmbedder(settings.embedding_dim)
    if settings.embedding_provider == "local":
        return LocalEmbedder(settings.embedding_model, settings.embedding_dim)
    raise NotImplementedError("EMBEDDING_PROVIDER=openai is documented but not implemented yet.")
