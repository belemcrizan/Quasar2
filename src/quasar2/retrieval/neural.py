"""Optional neural dense retriever behind the same search interface.

Hashing cosine remains the stdlib debug backend and must not be reported as neural.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Sequence

from quasar2.retrieval.base import (
    Document,
    SearchHit,
    filter_domain,
    validate_documents,
    validate_top_k,
)

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
        revision: str | None = None,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "NeuralDenseRetriever requires sentence-transformers. "
                "Install with: pip install 'quasar2[neural]'. "
                "Use backend 'dense_hash' for the stdlib debug path."
            ) from error
        if profile not in PROFILES:
            raise ValueError(f"Unknown neural profile {profile!r}; choose from {sorted(PROFILES)}")
        settings = PROFILES[profile]
        self.documents = validate_documents(documents)
        self.profile_id = settings["label"]
        self.model_name = model_name or str(settings["model_id"])
        self.device = device
        self.query_prefix = str(settings["query_prefix"])
        self.passage_prefix = str(settings["passage_prefix"])
        self.normalize = bool(settings["normalize"])
        model_kwargs = {"revision": revision} if revision is not None else {}
        self._model = SentenceTransformer(self.model_name, device=device, **model_kwargs)
        texts = [self.passage_prefix + document.searchable_text for document in self.documents]
        cache_key = hashlib.sha256(
            json.dumps(
                {
                    "cache_schema": 2,
                    "model": self.model_name,
                    "revision": revision,
                    "profile": profile,
                    "ids": [document.document_id for document in self.documents],
                    "texts": texts,
                    "query_prefix": self.query_prefix,
                    "passage_prefix": self.passage_prefix,
                    "normalize": self.normalize,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        import numpy as np

        # Unpinned models may change remotely under the same name. Require an
        # explicit revision for persistent reuse; use a commit hash for research.
        cache_path = (
            Path(cache_dir) / f"{cache_key}.npy" if cache_dir is not None and revision else None
        )
        matrix = None
        if cache_path is not None and cache_path.exists():
            try:
                matrix = np.load(cache_path, allow_pickle=False)
                if not self._valid_matrix(matrix):
                    matrix = None
            except (OSError, ValueError, EOFError):
                matrix = None
        if matrix is None:
            matrix = np.asarray(
                self._model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=self.normalize,
                    show_progress_bar=False,
                )
            )
            if not self._valid_matrix(matrix):
                raise ValueError("Encoder returned an invalid embedding matrix")
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                # Same-directory atomic publication prevents partial cache reads.
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(
                        dir=cache_path.parent, suffix=".npy", delete=False
                    ) as stream:
                        temporary = Path(stream.name)
                        np.save(stream, matrix, allow_pickle=False)
                    os.replace(temporary, cache_path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        self._matrix = matrix
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

    def _valid_matrix(self, matrix: object) -> bool:
        import numpy as np

        return (
            isinstance(matrix, np.ndarray)
            and matrix.ndim == 2
            and matrix.shape[0] == len(self.documents)
            and matrix.shape[1] > 0
            and np.issubdtype(matrix.dtype, np.floating)
            and bool(np.isfinite(matrix).all())
        )

    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        import numpy as np

        validate_top_k(top_k)
        indices = filter_domain(self.documents, domain)
        if top_k == 0 or not indices or not query.strip():
            return ()
        query_vector = self._model.encode(
            [self.query_prefix + query],
            convert_to_numpy=True,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
        )[0]
        query_vector = np.asarray(query_vector)
        if query_vector.shape != (self._matrix.shape[1],) or not np.isfinite(query_vector).all():
            raise ValueError("Encoder returned an invalid query vector")
        scores: list[tuple[float, int]] = []
        similarities = self._matrix[indices] @ query_vector
        for index, similarity in zip(indices, similarities):
            score = float(similarity)
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
        validate_top_k(k)
        if not hits or k == 0:
            return ()
        pairs = [(query, hit.document.searchable_text) for hit in hits]
        scores = [float(score) for score in self._model.predict(pairs)]
        ranked = sorted(
            zip(scores, hits), key=lambda item: (-item[0], item[1].document.document_id)
        )
        return tuple(
            SearchHit(
                document=hit.document,
                score=score,
                rank=rank,
                components={
                    **dict(hit.components),
                    "rerank": score,
                    "stage": 2.0,
                    "first_stage_rank": float(hit.rank),
                },
            )
            for rank, (score, hit) in enumerate(ranked[:k], start=1)
        )
