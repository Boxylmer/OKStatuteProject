from pathlib import Path
import unittest

from statute.statuteparser import StatuteParser
from statute.statute import Statute
from statute.structurers import StatuteBodyStructurer, StatuteReferenceStructurer


class TestPDFParsing(unittest.TestCase):
    def test_pdf_parsing(self):
        TITLE_21_CONSISTENCY_EXCEPTIONS = "§21-1168."
        statute_path = Path("docs") / "statutes"
        parser = StatuteParser(
            pdf_path=statute_path / "2024-21.pdf", cache_dir=statute_path / "cache"
        )
        res = parser.parse()

        statutes = []
        for title, name, body, history in res:
            if title in TITLE_21_CONSISTENCY_EXCEPTIONS:
                check_consistency = False
            else:
                check_consistency = True
            structured_body = StatuteBodyStructurer().structure(
                body, check_consistency=check_consistency
            )
            structured_title = StatuteReferenceStructurer().structure(title)

            # print(structured_body)

            # print(len(structured_body))
            st = Statute(
                reference=title, name=name, body=structured_body, history=history
            )
            statutes.append(st)
            # print(st.title, st.directory())

            # print(body)
            # print(st.get_text())
            # print(structured_body)
            # print()

        self.assertEqual(len(statutes), 1493)
