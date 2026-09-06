"""Retrieval regressions, using fake encoders without model downloads."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from quasar2.retrieval.base import Document, SearchHit
from quasar2.retrieval.bm25 import BM25Retriever
from quasar2.retrieval.dense import HashingDenseRetriever
from quasar2.retrieval.factory import build_retriever
from quasar2.retrieval.hybrid import HybridRetriever
from quasar2.retrieval.neural import NeuralDenseRetriever

DOCS = (Document("a", "science", "", "galaxy star"), Document("b", "other", "", "galaxy"))


class RetrievalContracts(unittest.TestCase):
    def test_empty_token_corpus(self):
        retriever = BM25Retriever((Document("empty", "science", "", "the and"),))
        self.assertEqual(retriever.search("star", top_k=5), ())

    def test_search_limits(self):
        for backend in ("bm25", "dense_hash", "hybrid"):
            retriever = build_retriever(DOCS, backend)
            self.assertEqual(retriever.search("galaxy", top_k=0), ())
            for invalid in (-1, True, 1.5):
                with self.subTest(backend=backend, invalid=invalid), self.assertRaises(ValueError):
                    retriever.search("galaxy", top_k=invalid)

    def test_invalid_bm25_parameters(self):
        for kwargs in ({"k1": -1}, {"k1": float("nan")}, {"b": 2}, {"b": float("inf")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                BM25Retriever(DOCS, **kwargs)

    def test_invalid_fusion_parameters(self):
        sparse = BM25Retriever(DOCS)
        for kwargs in (
            {"rrf_k": -1},
            {"rrf_k": 0.5},
            {"dense_weight": float("nan")},
            {"sparse_weight": float("inf")},
            {"dense_weight": 0, "sparse_weight": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                HybridRetriever(sparse, sparse, **kwargs)

    def test_disabled_backend_is_never_called(self):
        disabled = SimpleNamespace(search=lambda *a, **k: self.fail("disabled backend called"))
        sparse = BM25Retriever(DOCS)
        hybrid = HybridRetriever(sparse, disabled, dense_weight=0)
        self.assertEqual(len(hybrid.search("galaxy", top_k=10)), 2)
        self.assertEqual(hybrid.search("galaxy", top_k=0), ())

    def test_disabled_backend_cannot_inject_zero_score_hits(self):
        enabled = SimpleNamespace(search=lambda *a, **k: ())
        disabled = SimpleNamespace(search=lambda *a, **k: (SearchHit(DOCS[0], 1, 1),))
        self.assertEqual(
            HybridRetriever(enabled, disabled, dense_weight=0).search("x", top_k=1), ()
        )

    def test_factory_does_not_build_unused_dense_index(self):
        with patch("quasar2.retrieval.factory.HashingDenseRetriever", side_effect=AssertionError):
            self.assertIsInstance(build_retriever(DOCS, "bm25"), BM25Retriever)

    def test_hash_sign_is_not_determined_by_bucket(self):
        retriever = HashingDenseRetriever(DOCS, dimensions=32)
        signs = {}
        for i in range(2000):
            bucket, sign = retriever._bucket(f"feature-{i}")
            signs.setdefault(bucket, set()).add(sign)
        self.assertTrue(all(len(values) == 2 for values in signs.values()))

    def test_duplicate_ids_rejected(self):
        for cls in (BM25Retriever, HashingDenseRetriever):
            with self.subTest(cls=cls), self.assertRaises(ValueError):
                cls((DOCS[0], DOCS[0]))

    def test_domain_filter_and_deterministic_ties(self):
        docs = (Document("z", "x", "", "star"), Document("a", "x", "", "star"))
        for backend in ("bm25", "dense_hash", "hybrid"):
            retriever = build_retriever(docs, backend)
            self.assertEqual(
                [h.document.document_id for h in retriever.search("star", top_k=2)], ["a", "z"]
            )
            self.assertEqual(retriever.search("star", top_k=2, domain="absent"), ())


class NeuralCacheTests(unittest.TestCase):
    def setUp(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy optional")
        self.np = np
        self.encodes = []
        encodes = self.encodes

        class Encoder:
            def __init__(self, *args, **kwargs):
                pass

            def encode(self, texts, **kwargs):
                encodes.append(tuple(texts))
                return np.array([[len(t), 1.0] for t in texts], dtype=float)

        self.fake = SimpleNamespace(SentenceTransformer=Encoder)
        self.modules = patch.dict("sys.modules", {"sentence_transformers": self.fake})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_cache_invalidation_on_content_and_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = NeuralDenseRetriever(DOCS, cache_dir=tmp, revision="rev1")
            again = NeuralDenseRetriever(DOCS, cache_dir=tmp, revision="rev1")
            self.assertEqual(first.manifest.cache_key, again.manifest.cache_key)
            self.assertEqual(len(self.encodes), 1)
            changed = (Document("a", "science", "", "different text"), DOCS[1])
            second = NeuralDenseRetriever(changed, cache_dir=tmp, revision="rev1")
            third = NeuralDenseRetriever(changed, cache_dir=tmp, revision="rev2")
            self.assertNotEqual(first.manifest.cache_key, second.manifest.cache_key)
            self.assertNotEqual(second.manifest.cache_key, third.manifest.cache_key)
            self.assertEqual(len(self.encodes), 3)

    def test_corrupt_cache_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = NeuralDenseRetriever(DOCS, cache_dir=tmp, revision="rev1")
            path = Path(tmp) / f"{first.manifest.cache_key}.npy"
            for invalid in (b"partial write", None):
                if invalid:
                    path.write_bytes(invalid)
                else:
                    self.np.save(path, self.np.array([[float("nan")]]))
                rebuilt = NeuralDenseRetriever(DOCS, cache_dir=tmp, revision="rev1")
                self.assertEqual(rebuilt._matrix.shape, (2, 2))
                self.assertTrue(self.np.isfinite(rebuilt._matrix).all())

    def test_unpinned_model_does_not_reuse_disk_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            NeuralDenseRetriever(DOCS, cache_dir=tmp)
            NeuralDenseRetriever(DOCS, cache_dir=tmp)
            self.assertEqual(len(self.encodes), 2)

    def test_invalid_profile_rejected(self):
        with self.assertRaises(ValueError):
            NeuralDenseRetriever(DOCS, profile="typo")

    def test_zero_limit_and_missing_domain_skip_encoding(self):
        retriever = NeuralDenseRetriever(DOCS)
        calls = len(self.encodes)
        self.assertEqual(retriever.search("galaxy", top_k=0), ())
        self.assertEqual(retriever.search("galaxy", top_k=3, domain="missing"), ())
        self.assertEqual(len(self.encodes), calls)
