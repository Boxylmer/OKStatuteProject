from datetime import timedelta, datetime
import json
import os
import shutil
from pathlib import Path
import unittest


# statutetext
from statute.statutetext import StatuteText
from statute.statuteparser import StatuteParser, STATUTE_21_URL
from statute.statutecache import StatuteCache


class TestStatuteText(unittest.TestCase):
    TEST_TEXT_1 = [
        "A. There is hereby created the Sexual Assault Forensic Evidence (SAFE) Board within the Office of the Attorney General. The Board shall have the power and duty to:",
        "1. Examine the process for gathering and analyzing sexual assault forensic evidence kits in this state and work with members of the Legislature to draft proposed legislation to improve the response of medical and law enforcement systems to sexual assault;",
        "2. Develop a plan for the prioritization and acceptance of untested sexual assault forensic evidence kits identified in the statewide audit conducted by the Board;",
        "3. Identify possible procedures for the testing of anonymous sexual assault evidence kits;",
        "4. Identify possible improvements for victim access to evidence other than sexual assault forensic evidence kits including, but not limited to, police reports and other physical evidence;",
        "5. Identify additional rights of victims concerning the sexual assault forensic evidence kits testing process;",
        "6. Identify and pursue grants and other funding sources to address untested sexual assault forensic evidence kits, reduce testing wait times, provide victim notification, and improve efficiencies in the kit testing process; and",
        "7. Develop a comprehensive training plan for equipping and enhancing the work of law enforcement, prosecutors, victim advocates, Sexual Assault Nurse Examiners, and multidisciplinary Sexual Assault Response Teams (SARTs) across all jurisdictions within this state.",
        "B. In carrying out its duties and responsibilities, the Board shall:",
        "1. Promulgate rules establishing criteria for the collection of sexual assault forensic evidence subject to specific, in-depth review by the Board;",
        "2. Establish and maintain statistical information related to sexual assault forensic evidence collection including, but not limited to, demographic and medical diagnostic information;",
        "3. Establish procedures for obtaining initial information regarding the collection of sexual assault forensic evidence from medical and law enforcement entities;",
        "4. Review the policies, practices, and procedures of the medical and law enforcement systems and make specific recommendations to the entities comprising the medical and law enforcement systems for actions necessary to improve such systems;",
        "5. Review the extent to which the medical and law enforcement systems are coordinated and evaluate whether the state is efficiently discharging its sexual assault forensic evidence collection responsibilities;",
        "6. Request and obtain a copy of all records and reports pertaining to sexual assault forensic evidence including, but not limited to:",
        "a. hospital records,",
        "b. court records,",
        "c. local, state, and federal law enforcement records,",
        "d. medical and dental records, and",
        "e. emergency medical service records.",
        "Confidential information provided to the Board shall be maintained by the Board in a confidential manner as otherwise required by state and federal law. Any person damaged by disclosure of such confidential information by the Board or its members which is not authorized by law may maintain an action for damages, costs, and attorney fees pursuant to The Governmental Tort Claims Act;",
        "7. Maintain all confidential information, documents, and records in possession of the Board as confidential and not subject to subpoena or discovery in any civil or criminal proceedings; provided, however, such information, documents, and records otherwise available from other sources shall not be exempt from subpoena or discovery through such sources solely because such information, documents, and records were presented to or reviewed by the Board; and",
        "8. Exercise all incidental powers necessary and proper for the implementation and administration of the Sexual Assault Forensic Evidence (SAFE) Board.",
        "C. The review and discussion of individual cases of sexual assault evidence collection shall be conducted in executive session. All discussions of individual cases and any writings produced by or created for the Board in the course of determining a remedial measure to be recommended by the Board, as the result of a review of an individual case of sexual assault evidence collection, shall be privileged and shall not be admissible in evidence in any proceeding. All other business shall be conducted in accordance with the provisions of the Oklahoma Open Meeting Act. The Board shall periodically conduct meetings to discuss organization and business matters and any actions or recommendations aimed at improvement of the collection of sexual assault forensic evidence which shall be subject to the Oklahoma Open Meeting Act.",
        "D. The Board shall submit an annual statistical report on the incidence of sexual assault forensic evidence collection in this state for which the Board has completed its review during the past calendar year including its recommendations, if any, to medical and law enforcement systems. The Board shall also prepare and make available to the public an annual report containing a summary of the activities of the Board relating to the review of sexual assault forensic evidence collection and an evaluation of whether the state is efficiently discharging its sexual assault forensic evidence collection responsibilities. The report shall be completed no later than February 1 of the subsequent year.",
    ]

    def test_statute_text_conversion(self):
        st = StatuteText(self.TEST_TEXT_1)
        st.as_list()

        statute_text = st.as_text()
        statute_list = st.as_list()
        statute_json = st.as_json()

        new_st = StatuteText.from_json(statute_json)
        self.assertEqual(str(new_st.as_list()), str(st.as_list()))

        self.assertTrue(
            statute_text.endswith("subsequent year.")
        )  # checks if part D actually made it to the end
        self.assertTrue(
            statute_list[-1]["text"].endswith("February 1 of the subsequent year.")
        )  # checks the same as above, but for the list getter

    def test_statute_text_getters(self):
        st = StatuteText(self.TEST_TEXT_1)
        # st.get_text # already covered

        subsection_names = st.subsection_names()
        subsections = [st._get_subsection(sname) for sname in subsection_names]
        self.assertEqual(len(subsections), 24)

        self.assertEqual(
            subsection_names,
            [
                "A",
                "A.1",
                "A.2",
                "A.3",
                "A.4",
                "A.5",
                "A.6",
                "A.7",
                "B",
                "B.1",
                "B.2",
                "B.3",
                "B.4",
                "B.5",
                "B.6",
                "B.6.a",
                "B.6.b",
                "B.6.c",
                "B.6.d",
                "B.6.e",
                "B.7",
                "B.8",
                "C",
                "D",
            ],
        )

        self.assertIn(
            "Confidential information provided to the Board shall be maintained",
            st.as_text(),
        )

        self.assertEqual(
            st._get_subsection("A")["text"],
            "There is hereby created the Sexual Assault Forensic Evidence (SAFE) Board within the Office of the Attorney General. The Board shall have the power and duty to:",
        )
        self.assertEqual(
            st._get_subsection("B.3")["text"],
            "Establish procedures for obtaining initial information regarding the collection of sexual assault forensic evidence from medical and law enforcement entities;",
        )
        self.assertEqual(
            st._get_subsection("B.6.c")["text"],
            "local, state, and federal law enforcement records,",
        )
        self.assertEqual(
            st._get_subsection("B.7")["text"],
            "Maintain all confidential information, documents, and records in possession of the Board as confidential and not subject to subpoena or discovery in any civil or criminal proceedings; provided, however, such information, documents, and records otherwise available from other sources shall not be exempt from subpoena or discovery through such sources solely because such information, documents, and records were presented to or reviewed by the Board; and",
        )

        self.assertEqual(st._get_subsection("foo"), {})


class TestStatuteParser(unittest.TestCase):
    # easy case, 301
    EASY_TL21_ST301 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69082"
    )

    # 143 contains a nested list
    NESTED_TL_ST143 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=496306"
    )

    # 355 contains historical data at the end
    HISTORICAL_TL21_ST355 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69118"
    )

    # 385 has a break where it should be a continuation
    HISTORICAL_TL21_ST385 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69138"
    )

    # 405 literally says "first, second, third, fourth"
    LITERAL_TL21_ST_405 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69150"
    )

    # 465 contains weird \xa0 characters
    WEIRD_CHARACTERS_TL21_ST465 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=487695"
    )

    # 484.1 contains sections that should be cut off (Historical Data Laws 2009 instead of historical data)
    CONTAINS_HIST_TL21_ST401 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=455104"
    )

    # 498 / 499 contain numbers in (1), (2), format
    UNUSUAL_NUMBERING_TL21_ST499 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69195"
    )

    # statute with 2-101 as the section
    DASHED_NAME_TL29_ST2_101 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=77641"
    )

    # statute with 1-1-203 as the section and 27A as the title.
    WEIRD_TITLE_AND_SECTION_TL27A_ST_1_1_203 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=78939"
    )

    def test_from_oscn(self):
        st = StatuteParser.from_oscn(self.EASY_TL21_ST301)
        self.assertEqual(st.full_title, "Title 21. Crimes and Punishments")
        self.assertEqual(
            st.full_section,
            "Section 301 - Prevention of Legislative Meetings - Penalty",
        )

    def test_special_cases(self):
        st = StatuteParser.from_oscn(self.EASY_TL21_ST301)
        self.assertEqual(st.subsection_names(), [])
        self.assertEqual(st.parse_title()[0], "21")
        self.assertEqual(st.parse_title()[1], "Crimes and Punishments")
        self.assertEqual(st.parse_section()[0], "301")
        self.assertEqual(
            st.parse_section()[1], "Prevention of Legislative Meetings - Penalty"
        )

        st = StatuteParser.from_oscn(self.NESTED_TL_ST143)
        self.assertEqual(st.subsection_names()[2], "A.2")

        st = StatuteParser.from_oscn(self.HISTORICAL_TL21_ST355)
        self.assertEqual(st.subsection_names(), ["A", "B", "C"])

        st = StatuteParser.from_oscn(self.HISTORICAL_TL21_ST385)
        self.assertEqual(st.subsection_names(), ["1", "2"])

        st = StatuteParser.from_oscn(self.LITERAL_TL21_ST_405)
        self.assertEqual(st.subsection_names(), ["First", "Second", "Third", "Fourth"])

        st = StatuteParser.from_oscn(self.WEIRD_CHARACTERS_TL21_ST465)
        self.assertNotIn("\xa0", st.text())

        st = StatuteParser.from_oscn(self.CONTAINS_HIST_TL21_ST401)
        self.assertNotIn("Historical Data", st.text())
        self.assertEqual(st.parse_section()[0], "484.1")

        st = StatuteParser.from_oscn(self.UNUSUAL_NUMBERING_TL21_ST499)
        self.assertEqual(st.subsection_names(), ["a", "b", "c"])

        st = StatuteParser.from_oscn(self.DASHED_NAME_TL29_ST2_101)
        self.assertEqual(st.parse_section()[0], "2-101")

        st = StatuteParser.from_oscn(self.WEIRD_TITLE_AND_SECTION_TL27A_ST_1_1_203)
        self.assertEqual(st.parse_title()[0], "27A")
        self.assertEqual(st.parse_section()[0], "1-1-203")
        self.assertEqual(st.parse_citation(), "27A.1-1-203")
        
    def test_link_retrieval(self):
        links = StatuteParser.get_statute_links(STATUTE_21_URL)
        links_with_repealed =  StatuteParser.get_statute_links(STATUTE_21_URL, ignore_repealed=False)
        print(links)
        self.assertGreater(len(links), 2)
        self.assertGreater(len(links_with_repealed), len(links))
        

class TestStatuteCache(unittest.TestCase):
    # 484.1 contains sections that should be cut off (Historical Data Laws 2009 instead of historical data)
    CONTAINS_HIST_TL21_ST401 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=455104"
    )

    # 498 / 499 contain numbers in (1), (2), format
    UNUSUAL_NUMBERING_TL21_ST499 = (
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69195"
    )

    def setUp(self):
        self.test_dir = Path("test/cache_dir")
        self.cache = StatuteCache(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_cache_statute(self):
        parser = self.cache.get_statute(self.CONTAINS_HIST_TL21_ST401)
        title_section = parser.parse_citation()

        path = os.path.join(self.test_dir, f"{title_section}.json")
        self.assertTrue(os.path.exists(path))

        self.assertIn(title_section, self.cache.available_statutes())  # metadata check

    def test_get_statute_by_title_section(self):
        parser1 = self.cache.get_statute(self.CONTAINS_HIST_TL21_ST401)
        title_section = f"{parser1.parse_title()[0]}.{parser1.parse_section()[0]}"

        parser2 = self.cache.get_statute_by_citation(title_section)
        self.assertEqual(parser1.raw_text, parser2.raw_text)

    def test_force_refresh(self):
        parser1 = self.cache.get_statute(self.CONTAINS_HIST_TL21_ST401)
        parser2 = self.cache.get_statute(self.CONTAINS_HIST_TL21_ST401, force=True)

        self.assertEqual(parser1.parse_title(), parser2.parse_title())
        self.assertEqual(parser1.parse_section(), parser2.parse_section())

    def test_prune_cache(self):
        parser1 = self.cache.get_statute(self.CONTAINS_HIST_TL21_ST401)
        citation_str = parser1.parse_citation()

        # everything in this block is basically a @patch for the time of a document
        path = os.path.join(self.test_dir, f"{citation_str}.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["cached_at"] = (datetime.now() - timedelta(days=10)).isoformat(
            timespec="seconds"
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        ##################################################

        self.cache._load_cached_metadata()
        removed = self.cache.prune_cache(datetime.now() - timedelta(days=1))
        self.assertEqual(removed, 1)
        self.assertNotIn(citation_str, self.cache.available_statutes())
