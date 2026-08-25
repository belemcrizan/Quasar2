"""Optional neural dense retriever behind the same search interface.

Hashing cosine remains the stdlib debug backend.  This class is a paper-grade
dense path and is not imported by the default POC install.
"""

from __future__ import annotations

from typing import Sequence

from quasar2.retrieval.base import Document, SearchHit, filter_domain


class NeuralDenseRetriever:
    """Sentence-transformer cosine search with a frozen model name.

    Requires ``pip install 'quasar2[neural]'``.  The first call may download
    weights; pin ``model_name`` in config and record the revision in experiment
    metadata.  This backend is replaceable: the loop never depends on it.
    """

    def __init__(
        self,
        documents: Sequence[Document],
        *,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "NeuralDenseRetriever requires sentence-transformers. "
                "Install with: pip install 'quasar2[neural]'. "
                "Use backend 'dense_hash' for the stdlib debug path."
            ) from error
        self.documents = tuple(documents)
        self.model_name = model_name
        self.device = device
        self._model = SentenceTransformer(model_name, device=device)
        texts = [document.searchable_text for document in self.documents]
        self._matrix = self._model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )

    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        import numpy as np

        query_vector = self._model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )[0]
        scores: list[tuple[float, int]] = []
        for index in filter_domain(self.documents, domain):
            score = float(np.dot(query_vector, self._matrix[index]))
            if score > 0:
                scores.append((score, index))
        scores.sort(key=lambda item: (-item[0], self.documents[item[1]].document_id))
        return tuple(
            SearchHit(
                document=self.documents[index],
                score=score,
                rank=rank,
                components={"dense_neural": score},
            )
            for rank, (score, index) in enumerate(scores[:top_k], start=1)
        )
