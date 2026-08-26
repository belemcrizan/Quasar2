"""Optional neural dense retriever behind the same search interface.

Hashing cosine remains the stdlib debug backend and must not be reported as neural.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Sequence

from quasar2.retrieval.base import Document, SearchHit, filter_domain

PROFILES = {
    "minilm": {
        "model_id": "sentence-transformers/all-MiniLM-L6-v2",
        "query_prefix": "",
        "passage_prefix": "",
        "normalize": True,
        "label": "neural_minilm",
    },
    "e5": {
        "model_id": "intfloat/multilingual-e5-base",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "normalize": True,
        "label": "neural_e5",
    },
    "bge-m3": {
        "model_id": "BAAI/bge-m3",
        "query_prefix": "",
        "passage_prefix": "",
        "normalize": True,
        "label": "neural_bge_m3",
    },
}


@dataclass(frozen=True, slots=True)
class NeuralManifest:
    profile_id: str
    model_id: str
    revision: str | None
    device: str
    normalize: bool
    query_prefix: str
    passage_prefix: str
    n_documents: int
    cache_key: str


class NeuralDenseRetriever:
    """Sentence-transformer cosine search with a pinned profile.

    Requires ``pip install 'quasar2[neural]'``. HashingDenseRetriever is not this class.
    """

    def __init__(
        self,
        documents: Sequence[Document],
        *,
        model_name: str | None = None,
        device: str = "cpu",
        profile: str = "minilm",
        cache_dir: str | Path | None = None,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "NeuralDenseRetriever requires sentence-transformers. "
                "Install with: pip install 'quasar2[neural]'. "
                "Use backend 'dense_hash' for the stdlib debug path."
            ) from error
        settings = PROFILES.get(profile, PROFILES["minilm"])
        self.documents = tuple(documents)
        self.profile_id = settings["label"]
        self.model_name = model_name or str(settings["model_id"])
        self.device = device
        self.query_prefix = str(settings["query_prefix"])
        self.passage_prefix = str(settings["passage_prefix"])
        self.normalize = bool(settings["normalize"])
        self._model = SentenceTransformer(self.model_name, device=device)
        revision = None
        try:
            revision = getattr(self._model, "model_card_data", None) and None
            revision = getattr(getattr(self._model, "_model_card_vars", {}), "get", lambda *_: None)("model_revision")
        except Exception:
            revision = None
        texts = [self.passage_prefix + document.searchable_text for document in self.documents]
        cache_key = hashlib.sha256(
            json.dumps(
                {
                    "model": self.model_name,
                    "profile": profile,
                    "ids": [document.document_id for document in self.documents],
                    "normalize": self.normalize,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        cache_path = None
        if cache_dir is not None:
            cache_path = Path(cache_dir) / f"{cache_key}.npy"
        if cache_path is not None and cache_path.exists():
            import numpy as np

            self._matrix = np.load(cache_path)
        else:
            self._matrix = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
            )
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                import numpy as np

                np.save(cache_path, self._matrix)
        self.manifest = NeuralManifest(
            profile_id=self.profile_id,
            model_id=self.model_name,
            revision=str(revision) if revision else None,
            device=device,
            normalize=self.normalize,
            query_prefix=self.query_prefix,
            passage_prefix=self.passage_prefix,
            n_documents=len(self.documents),
            cache_key=cache_key,
        )

    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        import numpy as np

        query_vector = self._model.encode(
            [self.query_prefix + query],
            convert_to_numpy=True,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
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
                components={"dense_neural": score, "stage": 1.0},
            )
            for rank, (score, index) in enumerate(scores[:top_k], start=1)
        )


class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = "cpu") -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as error:
            raise RuntimeError("Reranker requires sentence-transformers CrossEncoder") from error
        self.model_name = model_name
        self.device = device
        self._model = CrossEncoder(model_name, device=device)
        self.profile_id = "reranker_bge_v2_m3"

    def rerank(self, query: str, hits: Sequence[SearchHit], k: int) -> tuple[SearchHit, ...]:
        if not hits:
            return ()
        pairs = [(query, hit.document.searchable_text) for hit in hits]
        scores = [float(score) for score in self._model.predict(pairs)]
        ranked = sorted(zip(scores, hits), key=lambda item: (-item[0], item[1].document.document_id))
        return tuple(
            SearchHit(
                document=hit.document,
                score=score,
                rank=rank,
                components={**dict(hit.components), "rerank": score, "stage": 2.0, "first_stage_rank": float(hit.rank)},
            )
            for rank, (score, hit) in enumerate(ranked[:k], start=1)
        )
