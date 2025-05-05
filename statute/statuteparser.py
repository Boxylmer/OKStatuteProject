import re
import requests  # type: ignore

from bs4 import BeautifulSoup, Tag, NavigableString

from statute.statutetext import StatuteText

BASE_URL = "https://www.oscn.net/"


class StatuteParser:
    def __init__(self, full_title: str, full_section: str, raw_texts: list[str]):
        self.full_title = full_title
        self.full_section = full_section
        self.raw_text = raw_texts
        self.statute_text = StatuteText(raw_texts)

    @staticmethod
    def from_html(html) -> "StatuteParser":
        soup = BeautifulSoup(html, "html.parser")
        main_content_div = soup.find(
            "div", id="oscn-content"
        )  # right now, everything I want is inside this div
        if not isinstance(main_content_div, Tag):
            raise (ValueError("oscn-content was not found in the html"))
        title, section = StatuteParser._parse_header_data(main_content_div)

        raw_texts = StatuteParser._parse_raw_body_data(main_content_div)

        return StatuteParser(title, section, raw_texts=raw_texts)

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
    def from_oscn(link: str) -> "StatuteParser":
        html = requests.get(link).text
        return StatuteParser.from_html(html)

    def formatted_text(self, **kwargs) -> str:
        return self.statute_text.as_text(**kwargs)

    def structured_text(self) -> list[dict]:
        return self.statute_text.structured_data

    # StatuteText wrappers
    def text_json(self):
        return self.statute_text.as_json()

    def text(self, subsection: str = "", pretty: bool = False, indent: int = 2):
        return self.statute_text.as_text(
            subsection=subsection, pretty=pretty, indent=indent
        )

    def subsection_names(self):
        return self.statute_text.subsection_names()

    def get_subsection(self, subsection_name):
        return self.statute_text._get_subsection(subsection_name=subsection_name)

    def parse_title(self) -> tuple[str, str]:
        """
        Extracts the title number and title label from a line like:
        'Title 124A. Crimes and Punishments'
        returns (title_id, title_description)
        """
        match = re.match(r"Title\s+([0-9A-Za-z]+)\.\s*(.+)", self.full_title)
        if not match:
            raise ValueError(f"Unrecognized title format: {self.full_title}")
        return match.group(1), match.group(2)

    def parse_section(self) -> tuple[str, str]:
        """
        Extracts the section number and label from a line like:
        'Section 301 - Prevention of Legislative Meetings - Penalty'
        returns (section_id, section_description)
        """
        match = re.match(r"Section\s+([0-9A-Za-z.-]+)\s*-\s*(.+)", self.full_section)
        if not match:
            raise ValueError(f"Unrecognized section format: {self.full_section}")
        return match.group(1), match.group(2)

    def parse_citation(self) -> str:
        return f"{self.parse_title()[0]}.{self.parse_section()[0]}"

    @staticmethod
    def get_statute_links(statute_title_url, ignore_repealed=True):
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
