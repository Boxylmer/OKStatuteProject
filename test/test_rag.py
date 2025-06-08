import unittest
import shutil
from pathlib import Path

from rag.rag import StatuteRAG
from rag.utils import (
    ensure_embedding_model,
    ensure_cross_encoder_model,
    cosine_similarity,
)
from statute.statute import Statute


TEST_DATA_DIR = Path("test/test_data")


class TestStatuteRAG(unittest.TestCase):
    TEXTS = [
        "Section A. All persons born in the United States are citizens.",
        "Section B. No person shall be denied equal protection under the law.",
        "Section C. The legislature shall enact laws for public safety.",
        "Section D. Property may not be taken for public use without compensation.",
        "Section E. The governor shall have the power to grant pardons.",
        "Section F. Every person has the right to free speech.",
        "Section G. The right to bear arms shall not be infringed.",
        "Section H. Excessive bail shall not be required.",
        "Section I. Trials shall be by an impartial jury.",
        "Section J. No law shall impair the obligation of contracts.",
        "Section K. Education shall be free and public.",
        "Section L. The state shall maintain a balanced budget.",
    ]

    def setUp(self):
        self.embedding_model = "sentence-transformers/all-mpnet-base-v2"
        self.reranking_model = "cross-encoder/ms-marco-TinyBERT-L2-v2"  # "cross-encoder/ms-marco-MiniLM-L-12-v2"  # this thing fails half of the time and makes things worse the other half
        self.db_path = Path("data") / "test_chroma_db"

        self.embedding_model_path = ensure_embedding_model(self.embedding_model)
        self.reranking_model_path = ensure_cross_encoder_model(self.reranking_model)
        self.statute_rag = StatuteRAG(
            db_path=self.db_path,
            embedding_model_name=self.embedding_model,
            reranking_model_name=self.reranking_model,
            collection_name="test",
        )
        self.statute_rag.reset()

    def tearDown(self):
        pass

    def test_embedding_model_downloaded(self):
        self.assertTrue(
            self.embedding_model_path.exists() and self.embedding_model_path.is_dir(),
            "Embedding model path should exist after download.",
        )

    def test_reranking_model_downloaded(self):
        self.assertTrue(
            self.reranking_model_path.exists() and self.reranking_model_path.is_dir(),
            "Reranking model path should exist after download.",
        )

    def test_cosine_similarity_function(self):
        vec1 = [1, 0, 0]
        vec2 = [1, 0, 0]
        vec3 = [0, 1, 0]
        self.assertAlmostEqual(cosine_similarity(vec1, vec2), 1.0)
        self.assertAlmostEqual(cosine_similarity(vec1, vec3), 0.0)

    def test_ingest_and_query(self):
        self.statute_rag._ingest(
            self.TEXTS, metadatas=[{"citation": i} for i in range(len(self.TEXTS))]
        )

        query = "What rights do people have regarding free speech?"
        results = self.statute_rag.query(query, top_k=3)
        self.assertTrue(len(results) > 0, "Query should return at least one result.")
        self.assertTrue(results[0][0].startswith("Section F"))

        query = "Which statute section covers censorship?"
        results = self.statute_rag.query(query, top_k=3)

        self.assertTrue(
            results[0][0].startswith("Section F")
            or results[1][0].startswith("Section F")
            or results[2][0].startswith("Section F"),
            f"started with: {results[0][0][0:30]}",
        )

        query = "Which statute section covers the act of posting bond?"
        results = self.statute_rag.query(query, top_k=3)
        self.assertTrue(
            results[0][0].startswith("Section H")  # -> returned section C
            or results[1][0].startswith("Section H")  # -> returned section B
            or results[2][0].startswith("Section H")  # -> returned section F
        )

    def test_ingest_statute(self):
        test_html_paths = [
            TEST_DATA_DIR / "21.2.143.html",
            TEST_DATA_DIR / "21.7.301.html",
        ]
        for path in test_html_paths:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
                example_parser = Statute.from_html(html)
                self.statute_rag.ingest_statute(example_parser)

        duplicate_statute_path = test_html_paths[0]
        with open(duplicate_statute_path, "r", encoding="utf-8") as f:
            # should raise
            with self.assertRaises(ValueError):
                html = f.read()
                self.statute_rag.ingest_statute(Statute.from_html(html))

            # should not raise with exist_ok
            self.statute_rag.ingest_statute(Statute.from_html(html), exist_ok=True)

        query = "What happens if I prevent a group of people from gathering together?"
        results = self.statute_rag.query(query, top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("felony", results[0][0])
        self.assertEqual(results[0][1]["citation"], "21.301")

        query = "How does oklahoma law prevent someone from being attacked?"
        results = self.statute_rag.query(query, top_k=2)
        self.assertEqual(len(results), 2)

        self.assertEqual(results[0][1]["citation"], "21.143")

    def test_similarity_indexing(self):
        embed_1 = self.statute_rag.embedding_model.embed_query("posting bond")
        embed_section_h = self.statute_rag.embedding_model.embed_query("excessive bail")

        embed_section_h = self.statute_rag.embedding_model.embed_query(
            "passage: Section H. Excessive bail shall not be required."
        )
        embed_1 = self.statute_rag.embedding_model.embed_query(
            "query: Which statute section covers the act of posting bail?"
        )
        embed_section_c = self.statute_rag.embedding_model.embed_query(
            "passage: Section C. The legislature shall enact laws for public safety."
        )

        correct_embedding = cosine_similarity(embed_1, embed_section_h)
        incorrect_embedding = cosine_similarity(embed_1, embed_section_c)
        self.assertGreater(correct_embedding, incorrect_embedding)

        embed_2 = "query: Which statute prohibits excessive bail?"
        embed_3 = "query: Which statute discusses posting bail?"

        embed_q2 = self.statute_rag.embedding_model.embed_query(embed_2)
        embed_q3 = self.statute_rag.embedding_model.embed_query(embed_3)

        self.assertGreater(
            cosine_similarity(embed_q2, embed_section_h),
            cosine_similarity(embed_q2, embed_section_c),
        )

        self.assertGreater(
            cosine_similarity(embed_q3, embed_section_h),
            cosine_similarity(embed_q3, embed_section_c),
        )

    def test_reranking_indexing(self):
        self.statute_rag._ingest(
            self.TEXTS, metadatas=[{"citation": i} for i in range(len(self.TEXTS))]
        )

        query = (
            "What does the law say about the governments ability to censor information?"
        )

        results_without_reranking = self.statute_rag.query(
            query, top_k=5, rerank_if_available=False
        )
        results_with_reranking = self.statute_rag.query(query, top_k=5)

        self.assertTrue(
            results_with_reranking[0][0].startswith("Section F"),
            f"started with: {results_with_reranking[0][0][0:30]}...",
        )
