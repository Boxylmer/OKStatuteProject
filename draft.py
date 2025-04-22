import re
from collections import deque
import requests  # type: ignore

from bs4 import BeautifulSoup, Tag, NavigableString

BASE_URL = "https://www.oscn.net/"
STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"


def get_statute_title_section_links(statute_title_url, ignore_repealed=True):
    response = requests.get(statute_title_url)
    soup = BeautifulSoup(response.text, "html.parser")
    statute_links = []

    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        href = link["href"]

        if ignore_repealed and text.strip().lower().endswith("repealed"):
            continue

        if (
            "DeliverDocument.asp?CiteID=" not in href
        ):  # i.e., is the link actually to a statute?
            continue

        full_url = BASE_URL + "/applications/oscn/" + href
        statute_links.append({"citation": text, "link": full_url})
    return statute_links


class StatuteText:
    SECTION_PATTERNS = [
        (r"^[A-Z]\.", 1),        # A., B., C.
        (r"^\d+\.", 2),          # 1., 2., 3.
        (r"^[a-z]\.", 3),        # a., b., c.
        (r"^\([A-Z]\)", 4),      # (A), (B) (rare, maybe used once)
        (r"^\([0-9]+\)", 5),     # (1), (2) (rare, used like once)
        (r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\.", 6),  # Ordinal
    ]

    def __init__(self, raw_texts: list[str]):
        self.raw_texts = raw_texts

    def _get_section_level(self, text: str) -> int:
        for pattern, level in self.SECTION_PATTERNS:
            if re.match(pattern, text.strip()):
                return level
        raise(ValueError(f"Pattern not seen before for raw text: '{text.strip()}'"))

    def _parse(self) -> list[dict]:
        root = []
        stack = deque()

        for line in self.raw_texts:
            level = self._get_section_level(line)
            node = {"text": line.strip(), "subsections": []}

            label = re.match(r"^([\w\(\)]+\.?)\s+(.*)", node["text"])
            if label:
                node["label"], node["text"] = label.groups()
            else:
                node["label"] = None # type: ignore

            while stack and stack[-1][1] >= level:
                stack.pop()

            if stack:
                stack[-1][0]["subsections"].append(node)
            else:
                root.append(node)

            stack.append((node, level))

        return root

    def structure(self) -> dict:
        return {"data": self._parse()}

test_texts = ['A. There is hereby created the Sexual Assault Forensic Evidence (SAFE) Board within the Office of the Attorney General. The Board shall have the power and duty to:', '1. Examine the process for gathering and analyzing sexual assault forensic evidence kits in this state and work with members of the Legislature to draft proposed legislation to improve the response of medical and law enforcement systems to sexual assault;', '2. Develop a plan for the prioritization and acceptance of untested sexual assault forensic evidence kits identified in the statewide audit conducted by the Board;', '3. Identify possible procedures for the testing of anonymous sexual assault evidence kits;', '4. Identify possible improvements for victim access to evidence other than sexual assault forensic evidence kits including, but not limited to, police reports and other physical evidence;', '5. Identify additional rights of victims concerning the sexual assault forensic evidence kits testing process;', '6. Identify and pursue grants and other funding sources to address untested sexual assault forensic evidence kits, reduce testing wait times, provide victim notification, and improve efficiencies in the kit testing process; and', '7. Develop a comprehensive training plan for equipping and enhancing the work of law enforcement, prosecutors, victim advocates, Sexual Assault Nurse Examiners, and multidisciplinary Sexual Assault Response Teams (SARTs) across all jurisdictions within this state.', 'B. In carrying out its duties and responsibilities, the Board shall:', '1. Promulgate rules establishing criteria for the collection of sexual assault forensic evidence subject to specific, in-depth review by the Board;', '2. Establish and maintain statistical information related to sexual assault forensic evidence collection including, but not limited to, demographic and medical diagnostic information;', '3. Establish procedures for obtaining initial information regarding the collection of sexual assault forensic evidence from medical and law enforcement entities;', '4. Review the policies, practices, and procedures of the medical and law enforcement systems and make specific recommendations to the entities comprising the medical and law enforcement systems for actions necessary to improve such systems;', '5. Review the extent to which the medical and law enforcement systems are coordinated and evaluate whether the state is efficiently discharging its sexual assault forensic evidence collection responsibilities;', '6. Request and obtain a copy of all records and reports pertaining to sexual assault forensic evidence including, but not limited to:', 'a. hospital records,', 'b. court records,', 'c. local, state, and federal law enforcement records,', 'd. medical and dental records, and', 'e. emergency medical service records.', 'Confidential information provided to the Board shall be maintained by the Board in a confidential manner as otherwise required by state and federal law. Any person damaged by disclosure of such confidential information by the Board or its members which is not authorized by law may maintain an action for damages, costs, and attorney fees pursuant to The Governmental Tort Claims Act;', '7. Maintain all confidential information, documents, and records in possession of the Board as confidential and not subject to subpoena or discovery in any civil or criminal proceedings; provided, however, such information, documents, and records otherwise available from other sources shall not be exempt from subpoena or discovery through such sources solely because such information, documents, and records were presented to or reviewed by the Board; and', '8. Exercise all incidental powers necessary and proper for the implementation and administration of the Sexual Assault Forensic Evidence (SAFE) Board.', 'C. The review and discussion of individual cases of sexual assault evidence collection shall be conducted in executive session. All discussions of individual cases and any writings produced by or created for the Board in the course of determining a remedial measure to be recommended by the Board, as the result of a review of an individual case of sexual assault evidence collection, shall be privileged and shall not be admissible in evidence in any proceeding. All other business shall be conducted in accordance with the provisions of the Oklahoma Open Meeting Act. The Board shall periodically conduct meetings to discuss organization and business matters and any actions or recommendations aimed at improvement of the collection of sexual assault forensic evidence which shall be subject to the Oklahoma Open Meeting Act.', 'D. The Board shall submit an annual statistical report on the incidence of sexual assault forensic evidence collection in this state for which the Board has completed its review during the past calendar year including its recommendations, if any, to medical and law enforcement systems. The Board shall also prepare and make available to the public an annual report containing a summary of the activities of the Board relating to the review of sexual assault forensic evidence collection and an evaluation of whether the state is efficiently discharging its sexual assault forensic evidence collection responsibilities. The report shall be completed no later than February 1 of the subsequent year.']
StatuteText(test_texts).structure()

class StatuteData:
    def __init__(self, title, section, raw_text):
        self.title = title
        self.section = section
        self.raw_text = raw_text

    @staticmethod
    def from_html(html) -> "StatuteData":
        soup = BeautifulSoup(html, "html.parser")
        main_content_div = soup.find(
            "div", id="oscn-content"
        )  # right now, everything I want is inside this div
        if not isinstance(main_content_div, Tag):
            raise (ValueError("oscn-content was not found in the html"))
        title, section = StatuteData._parse_header_data(main_content_div)

        raw_text = StatuteData._parse_raw_body_data(main_content_div)

        return StatuteData(title, section, raw_text=raw_text)

    @staticmethod
    def _parse_header_data(main_content_div: Tag) -> tuple[str, str]:
        # looks like inside a div called "document_header", theres a bunch of titles separated by <br> tags, but all in one <p>.
        organization_soup = main_content_div.find("div", class_="document_header").find(  # type: ignore
            "p"
        )

        organization_list = []
        current_text = ""
        for elem in organization_soup.descendants:
            if isinstance(elem, NavigableString):
                current_text += str(elem).strip().replace("\xa0", " ")

            elif isinstance(elem, Tag) and current_text:
                organization_list.append(current_text)
                current_text = ""

        if current_text:
            organization_list.append(current_text)

        title = next(
            (line for line in organization_list if line.startswith("Title")), ""
        )
        section = next(
            (line for line in organization_list if line.startswith("Section")), ""
        )

        missing = []
        if not title:
            missing.append("Title")
        if not section:
            missing.append("Section")

        if missing:
            print("DEBUG: organization_list =")
            for i, line in enumerate(organization_list):
                print(f"  [{i}]: {repr(line)}")
            raise ValueError(
                f"Missing required fields in header data: {', '.join(missing)}"
            )

        return (title, section)  # type: ignore

    @staticmethod
    def _parse_raw_body_data(main_content_div: Tag) -> list[str]:
        document_header_div = main_content_div.find("div", class_="document_header")
        if not document_header_div:
            raise ValueError("Could not find <div class='document_header'>")

        # Find the first <p> after the document header, regardless of nesting
        first_p = document_header_div.find_next("p")
        if not first_p:
            raise ValueError(
                "Could not find any <p> tag after <div class='document_header'>"
            )

        paragraph_bodies = []

        for el in first_p.find_all_next():
            el_text = (
                el.get_text(" ", strip=True)
                .replace("\n", "")
                .replace("\r", "")
                .replace("\xa0", "")
                .strip()
                .lower()
            )
            if el_text.startswith("historical data"):
                break

            if isinstance(el, Tag) and el.name == "p":
                cleaned_text = (
                    el.get_text(" ", strip=True)
                    .replace("\n", "")
                    .replace("\r", "")
                    .replace("\xa0", "")
                    .strip()
                )

                if cleaned_text:
                    paragraph_bodies.append(cleaned_text)

        return paragraph_bodies

    @staticmethod
    def _parse_title_text(raw_text: str):
        match = re.match(r"Title\s+([0-9A-Z]+)\.\s*(.+)", raw_text)
        if match:
            title_number = match.group(1)
            title_text = match.group(2)
        else:
            raise (
                ValueError(
                    f"The title '{raw_text}' was not parsable as a statute title."
                )
            )
        return title_number, title_text

    @staticmethod
    def from_oscn(link: str) -> "StatuteData":
        html = requests.get(link).text
        return StatuteData.from_html(html)

    @staticmethod
    def structure_text(raw_text: list[str]):
        ...




def run_example(link: str):
    statute = StatuteData.from_oscn(link)
    return statute.raw_text


subsections = get_statute_title_section_links(STATUTE_21_URL)

# easy case, 301
example_link = print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69082"
    )
)

# 143 contains a nested list
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=496306"
    )
)

# 355 contains historical data at the end
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69118"
    )
)

# 385 has a break where it should be a continuation
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69138"
    )
)

# 405 literally says "first, second, third, fourth"
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69150"
    )
)

# 465 contains weird \xa0 characters
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=487695"
    )
)

# 484.1 contains sections that should be cut off (Historical Data Laws 2009 instead of historical data)
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=455104"
    )
)

# 498 / 499 contain numebrs in (1), (2), format
print(
    run_example(
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69195"
    )
)

for i, subsection in enumerate(subsections):
    print(subsection["citation"])
    html = requests.get(subsection["link"]).text
    statute = StatuteData.from_html(html)
    print(f"Title: {statute.title}")
    print(f"Section: {statute.section}")
    print(f"Body: {statute.raw_text}")

    print("---------------------------------------------")


# TODO: Looks like 385 is a mistake on the websites part (like a lot of others), we can't bank on those mistakes ever really working. 
# So instead, it's probably best to just assume any non-pattern bullet is just a complete side-note and move it to the end at the root level. 
