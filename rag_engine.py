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

    Features:
    - Semantic retrieval using SentenceTransformers
    - Keyword fallback if embeddings unavailable
    - Region-aware filtering (e.g., India, EU, US)
    - Optional scoring boost for region-specific laws
    """

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self):
        self.guidelines = self._load_guidelines()
        self.embeddings = None
        self.model = None

        # Default region from env (optional)
        self.default_region = os.getenv("COMPLIANCE_REGION", None)

        if HAS_ST:
            self._build_index()
        else:
            print("[RAGEngine] sentence-transformers not found. Using keyword fallback.")

    def retrieve(self, query: str, top_k: int = 3, region: Optional[str] = None) -> list[dict]:
        """Return top-k relevant guideline chunks for a given query."""
        
        # Use passed region or fallback to env
        region = region or self.default_region

        # Step 1: filter guidelines if region specified
        guidelines = self._filter_by_region(region)

        if self.model and self.embeddings is not None:
            return self._semantic_retrieve(query, guidelines, top_k, region)

        return self._keyword_retrieve(query, guidelines, top_k)

    # ── Private ─────────────────────────────────────────

    def _load_guidelines(self) -> list[dict]:
        if GUIDELINES_PATH.exists():
            with open(GUIDELINES_PATH) as f:
                return json.load(f)
        return []

    def _filter_by_region(self, region: Optional[str]) -> list[dict]:
        """Filter guidelines by region keyword."""
        if not region:
            return self.guidelines

        filtered = [
            g for g in self.guidelines
            if region.lower() in g.get("regulation", "").lower()
        ]

        return filtered if filtered else self.guidelines  # fallback

    def _build_index(self):
        """Embed all guideline texts once at startup."""
        self.model = SentenceTransformer(self.MODEL_NAME)
        texts = [g["text"] for g in self.guidelines]

        if texts:
            self.embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

    def _semantic_retrieve(self, query: str, guidelines: list[dict], top_k: int, region: Optional[str]) -> list[dict]:
        """Semantic retrieval with optional region boosting."""

        query_vec = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        # Recompute embeddings for filtered guidelines
        texts = [g["text"] for g in guidelines]
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        scores = (embeddings @ query_vec.T).flatten()

        results = []
        for i, score in enumerate(scores):
            g = guidelines[i]

            # 🔥 Region boost (important)
            if region and region.lower() in g.get("regulation", "").lower():
                score *= 1.2

            results.append((score, g))

        # Sort by score
        results.sort(key=lambda x: x[0], reverse=True)

        return [
            {**g, "score": float(score)}
            for score, g in results[:top_k]
            if score > 0.3
        ]

    def _keyword_retrieve(self, query: str, guidelines: list[dict], top_k: int) -> list[dict]:
        """Fallback retrieval using keyword overlap."""

        query_words = set(query.lower().split())
        scored = []

        for g in guidelines:
            text_words = set(g["text"].lower().split())
            overlap = len(query_words & text_words)

            if overlap > 0:
                scored.append((overlap, g))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {**item, "score": float(score)}
            for score, item in scored[:top_k]
        ]