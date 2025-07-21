import unittest
from pathlib import Path
import textwrap

from statute.structurers import StatuteBodyStructurer, StatuteReferenceStructurer
from statute.utils import match_string_prefix_fuzzy

TEST_DATA_DIR = Path("test/test_data")


class TestUtils(unittest.TestCase):
    def test_match_string_prefix_fuzzy(self):
        # exact match
        self.assertEqual(
            match_string_prefix_fuzzy("The quick brown fox", "The quick"), 9
        )

        # \n and spaces in body
        body = "The\n   quick\nbrown fox"
        prefix = "The quick brown"
        self.assertEqual(match_string_prefix_fuzzy(body, prefix), 18)

        # nospace in body
        body = "Thequickbrownfox"
        prefix = "The quick brown"
        self.assertEqual(match_string_prefix_fuzzy(body, prefix), 13)

        # lots of bad spacing
        body = "  The \n quick\tbrown   fox"
        prefix = " The  quick brown"
        self.assertEqual(match_string_prefix_fuzzy(body, prefix), 19)

        # misalignment
        self.assertEqual(match_string_prefix_fuzzy("Hello world", "Hello m"), None)

        # prefix longer than body
        self.assertEqual(match_string_prefix_fuzzy("Short", "Short but longer"), None)

        # exact match
        self.assertEqual(
            match_string_prefix_fuzzy(
                "Statute Title\nStatute Name\nRest of text",
                "Statute Title Statute Name",
            ),
            26,
        )


class TestStatuteStructurer(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parse(self):
        text = textwrap.dedent(
            """
            A crime or public offense is an act or omission forbidden by
            law, and to which is annexed, upon conviction, either of the
            following punishments:
                1. Death;
                2. Imprisonment;
                3. Fine;

                4. Removal from office; or
                5. Disqualification to hold and enjoy any office of honor,
            trust, or profit, under this state.
        """
        )

        structured = StatuteBodyStructurer().structure(raw_body_text=text)
        self.assertEqual(structured[0]["label"], "")
        self.assertEqual(len(structured), 1)
        self.assertEqual(len(structured[0]["subsections"]), 5)
        self.assertEqual(structured[0]["subsections"][0]["label"], "1")
        self.assertEqual(structured[0]["subsections"][1]["label"], "2")


class TestTitleStructurer(unittest.TestCase):
    def test_statute_title_structurer(self):
        ans = StatuteReferenceStructurer().structure("§21-54.1v2")
        self.assertEqual(ans, {'title': '21', 'section': '54.1', 'version': '2'})

        ans = StatuteReferenceStructurer().structure("§21-123a.")
        self.assertEqual(ans, {'title': '21', 'section': '123a', 'version': None})

        ans = StatuteReferenceStructurer().structure("§63-312.5:")
        self.assertEqual(ans, {'title': '63', 'section': '312.5', 'version': None})
