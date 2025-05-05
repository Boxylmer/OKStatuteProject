import unittest
import shutil
from pathlib import Path
from rag.rag import StatuteRAG
from rag.utils import download_embedding_model
from statute.statuteparser import StatuteParser

TEST_DATA_DIR = Path("test/test_data")


class TestStatuteRAG(unittest.TestCase):
    def setUp(self):
        self.model_name = "sentence-transformers/all-mpnet-base-v2"
        self.model_dir = Path("data") / "embedding_models"
        self.db_path = Path("data") / "test_chroma_db"

        self.model_path = download_embedding_model(self.model_name, self.model_dir)
      

    def tearDown(self):
        shutil.rmtree(self.db_path, ignore_errors=True)

    def test_model_downloaded(self):
        model_path = Path(self.model_dir) / self.model_name.replace("/", "_")
        self.assertTrue(
            model_path.exists() and model_path.is_dir(),
            "Model path should exist after download.",
        )

    def test_ingest_and_query(self):
        texts = [
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
        rag = StatuteRAG(
            model_name=self.model_name,
            model_path=self.model_dir, 
            persist=False
        )
        rag._ingest(texts)

        query = "What rights do people have regarding free speech?"
        results = rag.query(query, top_k=3)
        self.assertTrue(len(results) > 0, "Query should return at least one result.")
        self.assertTrue(results[0][0].startswith("Section F"))

        query = "Which statute section covers censorship?"
        results = rag.query(query, top_k=3)
        self.assertTrue(results[0][0].startswith("Section F"))

        query = "Which statute section covers the act of posting bond?"
        results = rag.query(query, top_k=3)
        self.assertTrue(
            results[0][0].startswith("Section H")
            or results[1][0].startswith("Section H")
            or results[2][0].startswith("Section H")
        )

    def test_ingest_statute(self):
        rag = StatuteRAG(
            model_name=self.model_name, model_path=self.model_dir, persist=False
        )
        test_html_paths = [
            TEST_DATA_DIR / "21.2.143.html",
            TEST_DATA_DIR / "21.7.301.html",
        ]
        for path in test_html_paths:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
                example_parser = StatuteParser.from_html(html)
                rag.ingest_statute(example_parser)

        query = "What happens if I prevent a group of people from gathering together?"
        results = rag.query(query, top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("felony", results[0][0])
        self.assertEqual(results[0][1]["citation"], "21.301")


        query = "How does oklahoma law prevent someone from being attacked?"
        results = rag.query(query, top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][1]["citation"], "21.143")