from pathlib import Path
import unittest
import tempfile
import shutil
import json

from statute.title import Title
from statute.statute import Statute 



TITLE_21_PATH = Path("docs") / "statutes" / "2024-21.pdf"
TITLE_15_PATH = Path("docs") / "statutes" / "2024-15.pdf"


class TestTitle(unittest.TestCase):
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
                                {"title": "15", "section": "1A-C", "version": None, "subsection": ""}
                            ],
                        }
                    ],
                    "references": []
                }
            ],
            history="R.L."
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
            history="R.L."
        )

        self.title = Title([self.statute1, self.statute2])


    def test_caching_and_loading(self):
        TITLE_21_CONSISTENCY_EXCEPTIONS = "§21-1168."
        title = Title.from_pdf(TITLE_21_PATH, check_exemptions=TITLE_21_CONSISTENCY_EXCEPTIONS)
        
        with tempfile.TemporaryDirectory() as tempdir:
            cache_path = Path(tempdir)

            title.save_cache(cache_path / "cache")
            self.assertTrue(cache_path.exists())

            loaded_title = Title.from_cache(cache_path / "cache")

            self.assertEqual(len(loaded_title.statutes), len(title.statutes))

            # Should resolve the same text
            text = loaded_title.get_reference_text(
                section_reference={"title": "21", "section": "2", "version": None},
                subsection_reference=""
            )
            self.assertIn("No act or omission shall ", text)
