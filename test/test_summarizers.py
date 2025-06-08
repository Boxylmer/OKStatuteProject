from datetime import timedelta, datetime
import json
import os
import shutil
from pathlib import Path
import unittest


# statutetext
from nlp.summarizers import StatuteSummarizer, IRRELEVANT_TOKEN
from statute.statute import Statute

TEST_DATA_DIR = Path("test/test_data")


class TestStatuteSummarizer(unittest.TestCase):
    def test_summary(self):
        test_html_path = TEST_DATA_DIR / "21.2.143.html"
        with open(test_html_path, "r", encoding="utf-8") as f:
            html = f.read()
            example_statute = Statute.from_html(html)
        print(example_statute.formatted_text())
        summarizer = StatuteSummarizer(model="adrienbrault/saul-instruct-v1:Q4_K_M")
        print(summarizer.summarize(example_statute, verbose=True))

        summary_no_context = summarizer.summarize(
            example_statute,
            "My client is in breach of contract for not fully paying for an order of Rearden Steel.",
            verbose=True,
        )
        self.assertEqual(summary_no_context, IRRELEVANT_TOKEN)
