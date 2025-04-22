import re
import requests  # type: ignore

from typing import List, Optional

from bs4 import BeautifulSoup, Tag, NavigableString, Comment

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
        organization_soup = main_content_div.find("div", class_="document_header").find(
            "p"
        )  # type: ignore

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


    # @staticmethod
    # def _parse_raw_body_data(main_content_div: Tag) -> list[str]:
    #     # the body of all statutes, for some reason, have these comments in them
    #     begin_comment = next(
    #         (el for el in main_content_div.descendants if isinstance(el, Comment) and "BEGIN DOCUMENT" in el),
    #         None,
    #     )
    #     end_comment = next(
    #         (el for el in main_content_div.descendants if isinstance(el, Comment) and "END DOCUMENT" in el),
    #         None,
    #     )

    #     if not begin_comment or not end_comment:
    #         raise ValueError("BEGIN or END DOCUMENT comment not found")


    #     body_elements = []
    #     for el in begin_comment.next_siblings:
    #         if el == end_comment:
    #             break
    #         if isinstance(el, Tag):
    #             body_elements.append(el)

    #     paragraph_bodies = []
    #     for tag in body_elements:
            
    #         if tag.get_text().lower().strip() == "historical data":
    #             break
            
    #         if tag.name == "p":
    #             text = tag.get_text(" ", strip=True)
    #             text = text.replace("\n", "").replace("\r", "").strip()
    #             if text:
    #                 paragraph_bodies.append(text)


    #     return paragraph_bodies

    @staticmethod
    def _parse_raw_body_data(main_content_div: Tag) -> list[str]:
        document_header_div = main_content_div.find("div", class_="document_header")
        if not document_header_div:
            raise ValueError("Could not find <div class='document_header'>")

        # Find the first <p> after the document header, regardless of nesting
        first_p = document_header_div.find_next("p")
        if not first_p:
            raise ValueError("Could not find any <p> tag after <div class='document_header'>")

        paragraph_bodies = []

        for el in first_p.find_all_next():
            
            el_text = el.get_text(" ", strip=True).replace("\n", "").replace("\r", "").strip().lower()
            if el_text == "historical data":
                break

            if isinstance(el, Tag) and el.name == "p":
                cleaned_text = el.get_text(" ", strip=True).replace("\n", "").replace("\r", "").strip()
                # if cleaned_text.lower() == "historical data":
                #     break

                if cleaned_text:
                    paragraph_bodies.append(cleaned_text)

            

            # # Only collect text from <p> tags
            # if el.name == "p":
            #     if el_text:
            #         paragraph_bodies.append(el_text)

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


def run_example(link: str): 
    statute = StatuteData.from_oscn(link)
    return statute.raw_text

subsections = get_statute_title_section_links(STATUTE_21_URL)

# easy case, 301
example_link = print(run_example("https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69082"))

# 143 contains a nested list
print(run_example("https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=496306"))

# 355 contains historical data at the end
print(run_example("https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=69118"))

# 385 has a break where it should be a continuation

# 405 literally says "first, second, third, fourth"

# 465 contains weird \xa0 characters

# 484.1 contains sections that should eb cut off (Historical Data Laws 2009 instead of historical data)

# 498 / 499 contain numebrs in (1), (2), format


for i, subsection in enumerate(subsections):
    print(subsection["citation"])
    html = requests.get(subsection["link"]).text
    statute = StatuteData.from_html(html)
    print(f"Title: {statute.title}")
    print(f"Section: {statute.section}")
    print(f"Body: {statute.raw_text}")

    print("---------------------------------------------")
