from pathlib import Path
import unittest
import tempfile
import shutil
import json

from statute.title import Title
from statute.statute import Statute


TITLE_21_PATH = Path("docs") / "statutes" / "2024-21.pdf"
TITLE_15_PATH = Path("docs") / "statutes" / "2024-15.pdf"
TEST_DATA_DIR = Path("test") / "data"

class TestTitle(unittest.TestCase):
    TITLE_21_CONSISTENCY_EXCEPTIONS = "§21-1168."

    def setUp(self):
        self.statute1 = Statute(
            reference={"title": "21", "section": "4", "version": None},
            name="Unlawful Acts",
            body=[
                {
                    "label": "",
                    "text": "Main statute body",
                    "subsections": [
                        {
                            "label": "A",
                            "text": "Subsection A text",
                            "subsections": [],
                            "references": [
                                {
                                    "title": "15",
                                    "section": "1A-C",
                                    "version": None,
                                    "subsection": "",
                                }
                            ],
                        }
                    ],
                    "references": [],
                }
            ],
            history="R.L.",
        )

        self.statute2 = Statute(
            reference={"title": "15", "section": "1A-C", "version": None},
            name="Consumer Rights",
            body=[
                {
                    "label": "",
                    "text": "General consumer protections",
                    "subsections": [],
                }
            ],
            history="R.L.",
        )

        self.title = Title(cache_dir=TEST_DATA_DIR)
        self.title._add_statute(self.statute1)
        self.title._add_statute(self.statute2)

    def test_caching_and_loading(self):
        # Make a temporary directory to do this in
        title = Title(TEST_DATA_DIR)
        temp_cache_dir = title.cache_dir
        title.import_from_pdf(
            TITLE_21_PATH, check_exemptions=self.TITLE_21_CONSISTENCY_EXCEPTIONS
        )

        title.save_cache()
        self.assertTrue(title.cache_dir.exists())

        loaded_title = Title(temp_cache_dir)

        self.assertEqual(len(loaded_title.statute_registry), len(title.statute_registry))


        text = loaded_title.get_reference_text(
            section_reference={"title": "21", "section": "2", "version": None},
            subsection_reference="",
        )
        self.assertIn("No act or omission shall ", text)

    def test_reference_getter(self):
        title = Title(TEST_DATA_DIR)
        title.import_from_pdf(
            TITLE_21_PATH, check_exemptions=self.TITLE_21_CONSISTENCY_EXCEPTIONS
        )
        # title = Title.from_pdf(
        #     TITLE_21_PATH, check_exemptions=self.TITLE_21_CONSISTENCY_EXCEPTIONS
        # )

        self.assertTrue(
            title.get_reference_text({"title": "21", "section": "2200"}).startswith(
                "A. There is hereby created the Oklahoma Organized Retail Crime Task Force"
            )
        )

        self.assertTrue(
            title.get_reference_text(
                section_reference={"title": "21", "section": "2200"},
                subsection_reference="A",
            ).startswith(
                "A. There is hereby created the Oklahoma Organized Retail Crime Task Force"
            )
        )
        self.assertTrue(
            title.get_reference_text(
                section_reference={"title": "21", "section": "2200"},
                subsection_reference="B.2",
            ).startswith("2. Two members appointed by the President")
        )
