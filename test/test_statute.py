from datetime import timedelta, datetime
import json
import os
import shutil
from pathlib import Path
import unittest


# statutetext
from statute.statutetext import StatuteText
from statute.statuteparser import StatuteParser
from statute.statutecache import StatuteCache

STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"


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

    TEST_TEXT_2 = [
        "Test sentence no header",
        "A. When a court of competent jurisdiction has entered an order compelling a parent to furnish child support, necessary food, clothing, shelter, medical support, payment of child care expenses, or other remedial care for the minor child of the parent:",
        "1. Proof that:",
        "a. the order was made, filed, and served on the parent,",
        "b. the parent had actual knowledge of the existence of the order,",
        "c. the order was granted by default after prior due process notice to the parent, or",
        "d. the parent was present in court at the time the order was pronounced; and",
        "2. Proof of noncompliance with the order,",
        "shall be prima facie evidence of an indirect civil contempt of court.",
        "B. 1. In the case of indirect contempt for the failure to comply with an order for child support, child support arrears, or other support, punishment shall be, at the discretion of the court:",
        "a. incarceration in the county jail not exceeding six (6) months, or",
        "b. incarceration in the county jail on weekends or at other times that allow the obligor to be employed, seek employment or engage in other activities ordered by the court.",
        "2. Punishment may also include imposition of a fine in a sum not exceeding Five Hundred Dollars ($500.00).",
        "3. In the case of indirect contempt for the failure to comply with an order for child support, child support arrears, or other support, if the court finds by a preponderance of the evidence that the obligor is willfully unemployed, the court may require the obligor to work two (2) eight-hour days per week in a community service program as defined in Section 339.7 of Title 19 of the Oklahoma Statues, if the county commissioners of that county have implemented a community service program.",
        "C. 1. During proceedings for indirect contempt of court, the court may order the obligor to complete an alternative program and comply with a payment plan for child support and arrears. If the obligor fails to complete the alternative program and comply with the payment plan, the court shall proceed with the indirect contempt and shall impose punishment pursuant to subsection B of this section.",
        "2. An alternative program may include:",
        "a. a problem-solving court program for obligors when child support services under the state child support plan as provided in Section 237 of Title 56 of the Oklahoma Statutes are being provided for the benefit of the child. A problem-solving court program is an immediate and highly structured judicial intervention process for the obligor and requires completion of a participation agreement by the obligor and monitoring by the court. A problem-solving court program differs in practice and design from the traditional adversarial contempt prosecution and trial systems. The problem-solving court program uses a team approach administered by the judge in cooperation with a child support state\u0092s attorney and a child support court liaison who focuses on removing the obstacles causing the nonpayment of the obligor. The obligors in this program shall be required to sign an agreement to participate in this program as a condition of the Department of Human Services agreement to stay contempt proceedings or in lieu of incarceration after a finding of guilt. The court liaisons assess the needs of the obligor, develop a community referral network, make referrals, monitor the compliance of the obligor in the program, and provide status reports to the court, and",
        "b. participation in programs such as counseling, treatment, educational training, social skills training or employment training to which the obligor reports daily or on a regular basis at specified times for a specified length of time.",
        "D. In the case of indirect contempt for the failure to comply with an order for child support, child support arrears, or other support, the Supreme Court shall promulgate guidelines for determination of the sentence and purge fee. If the court fails to follow the guidelines, the court shall make a specific finding stating the reasons why the imposition of the guidelines would result in inequity. The factors that shall be used in determining the sentence and purge fee are:",
        "1. The proportion of the child support, child support arrearage payments, or other support that was unpaid in relation to the amount of support that was ordered paid;",
        "2. The proportion of the child support, child support arrearage payments, or other support that could have been paid by the party found in contempt in relation to the amount of support that was ordered paid;",
        "3. The present capacity of the party found in contempt to pay any arrearages;",
        "4. Any willful actions taken by the party found in contempt to reduce the capacity of that party to pay any arrearages;",
        "5. The past history of compliance or noncompliance with the support order; and",
        "6. Willful acts to avoid the jurisd`iction of the court."
    ]

    def test_statute_text_conversion(self):
        st = StatuteText(self.TEST_TEXT_1)
        st.as_list()

        statute_text = st.as_text()
        statute_list = st.as_list()
        statute_json = st.as_json()
        print(statute_json)
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

    def test_statute_text_walk_sections(self):
        st = StatuteText(self.TEST_TEXT_1)
        all_sections = list(st.walk_sections(append_parents=True, leaf_only=False))
        leaf_sections = list(st.walk_sections(append_parents=True, leaf_only=True))
        minimal_sections = list(st.walk_sections(append_parents=False, leaf_only=False))
        self.assertEqual(len(all_sections), len(minimal_sections))
        self.assertGreater(len(all_sections), len(leaf_sections))

        # [print(s) for s in all_sections]
        # print()
        # [print(s) for s in leaf_sections]
        # print()
        # [print(s) for s in minimal_sections]

        [print(s) for s in StatuteText(self.TEST_TEXT_2).walk_sections(append_parents=True, leaf_only=True)]

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
        self.cache.cache_dates[citation_str] = data["cached_at"]
        ##################################################

        self.cache._load_cached_metadata()
        removed = self.cache.prune_cache(datetime.now() - timedelta(days=1))
        self.assertEqual(removed, 1)
        self.assertNotIn(citation_str, self.cache.available_statutes())
        self.assertNotIn(citation_str, self.cache.citations)
        self.assertNotIn(citation_str, self.cache.cache_dates)
        self.assertNotIn(self.CONTAINS_HIST_TL21_ST401, self.cache.cached_links)

    def test_registry_updates_on_add(self):
        parser = self.cache.get_statute(self.CONTAINS_HIST_TL21_ST401)
        citation = parser.parse_citation()

        # Check citation added to internal registry
        self.assertIn(citation, self.cache.citations)
        self.assertIn(citation, self.cache.cache_dates)
        self.assertIn(self.CONTAINS_HIST_TL21_ST401, self.cache.cached_links)
        self.assertEqual(self.cache.cached_links[self.CONTAINS_HIST_TL21_ST401], citation)

