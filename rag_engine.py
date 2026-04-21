import json
import os
import numpy as np
from pathlib import Path
from typing import Optional

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False


GUIDELINES_PATH = Path(__file__).parent / "compliance_guidelines.json"


class RAGEngine:
    """
    Retrieval-Augmented Generation layer.
    Embeds compliance guidelines locally using SentenceTransformers,
    then retrieves the most relevant guidelines for each document section.

    Falls back to keyword-based retrieval if sentence-transformers is not installed.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"  # Tiny, fast, good quality — ~80MB

    def __init__(self):
        self.guidelines = self._load_guidelines()
        self.embeddings = None
        self.model = None

        if HAS_ST:
            self._build_index()
        else:
            print("[RAGEngine] sentence-transformers not found. Using keyword fallback.")

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """Return top-k relevant guideline chunks for a given query."""
        if self.model and self.embeddings is not None:
            return self._semantic_retrieve(query, top_k)
        return self._keyword_retrieve(query, top_k)

    # ── Private ──────────────────────────────────────────────────────────────

    def _load_guidelines(self) -> list[dict]:
        if GUIDELINES_PATH.exists():
            with open(GUIDELINES_PATH) as f:
                return json.load(f)
        return []

    def _build_index(self):
        """Embed all guideline texts once at startup."""
        self.model = SentenceTransformer(self.MODEL_NAME)
        texts = [g["text"] for g in self.guidelines]
        if texts:
            self.embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def _semantic_retrieve(self, query: str, top_k: int) -> list[dict]:
        query_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        scores = (self.embeddings @ query_vec.T).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {**self.guidelines[i], "score": float(scores[i])}
            for i in top_indices
            if scores[i] > 0.3
        ]

    def _keyword_retrieve(self, query: str, top_k: int) -> list[dict]:
        query_words = set(query.lower().split())
        scored = []
        for g in self.guidelines:
            text_words = set(g["text"].lower().split())
            overlap = len(query_words & text_words)
            if overlap > 0:
                scored.append((overlap, g))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]
