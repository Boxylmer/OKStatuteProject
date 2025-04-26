from collections import deque
import json
import re
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
        (r"^\([A-Z]\)", 4),      # (A), (B)
        (r"^\([0-9]+\)", 5),     # (1), (2)
        (r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\.", 6),  # Ordinal
    ]

    def __init__(self, raw_texts: list[str]):
        self.structured_data = self._parse(raw_texts)

    def _get_section_level(self, text: str) -> int:
        for pattern, level in self.SECTION_PATTERNS:
            if re.match(pattern, text.strip()):
                return level
        return 0

    def _clean_label(self, label: str) -> str:
        return re.sub(r"[().]", "", label).rstrip(".")

    def _parse(self, raw_texts) -> list[dict]:
        root = []
        stack = deque()
        orphans = []
        seen_structure = False

        for line in raw_texts:
            line = line.strip()
            level = self._get_section_level(line)

            if level == 0:
                if seen_structure:
                    orphans.append({"label": None, "text": line, "subsections": []})
                    continue
                else:
                    root.append({"label": None, "text": line, "subsections": []})
                    continue

            seen_structure = True
            node = {"text": line, "subsections": []}
            label_match = re.match(r"^([\w\(\)\.]+)\s+(.*)", line)

            if label_match:
                raw_label, content = label_match.groups()
                node["label"] = self._clean_label(raw_label)
                node["text"] = content
            else:
                node["label"] = None

            while stack and stack[-1][1] >= level:
                stack.pop()

            if stack:
                stack[-1][0]["subsections"].append(node)
            else:
                root.append(node)

            stack.append((node, level))

        root.extend(orphans)
        return root

    def as_dict(self) -> dict:
        return {"data": self.structured_data}

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    @staticmethod
    def from_json(json_str: str) -> "StatuteText":
        data = json.loads(json_str)
        instance = StatuteText([])
        instance.structured_data = data["data"]
        return instance

    def subsections(self) -> list[str]:
        results = []

        def walk(nodes, path=[]):
            for node in nodes:
                label = node.get("label")
                new_path = path + [label] if label else path
                if label:
                    results.append(".".join(new_path))
                walk(node.get("subsections", []), new_path)

        walk(self.structured_data)
        return results

    def get_subsection(self, subsection: str) -> dict | None:
        target = subsection.split(".")

        def find(nodes, path):
            for node in nodes:
                if node.get("label") == path[0]:
                    if len(path) == 1:
                        return node
                    return find(node.get("subsections", []), path[1:])
            return None

        return find(self.structured_data, target)
    
    def get_text(self, subsection: str = "", pretty: bool = False, indent: int = 2) -> str:
        data = self.as_dict()["data"]

        if not subsection:
            nodes = data
        else:
            node = self.get_subsection(subsection)
            if not node:
                return ""
            nodes = [node]

        def render(node, level=0):
            label = node.get("label")
            text = node.get("text", "")
            prefix = f"{label}. " if label else ""
            line = f"{prefix}{text}".strip()

            if pretty:
                pad = " " * (indent * level)
                lines = [f"{pad}{line}"]
                for child in node.get("subsections", []):
                    lines.append(render(child, level + 1))
                return "\n".join(lines)
            else:
                lines = [line]
                for child in node.get("subsections", []):
                    lines.append(render(child, level + 1))
                return " ".join(lines)

        rendered = [render(node) for node in nodes]
        return "\n\n".join(rendered) if pretty else " ".join(rendered)


class StatuteParser:

    def __init__(self, title: str, section: str, raw_texts: list[str]):
        self.title = title
        self.section = section
        self.raw_text = raw_texts
        self.formatted_data = StatuteText(raw_texts)

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
        return self.formatted_data.get_text( **kwargs)


class StatuteCache:
    # Cache a set of html documents based on title and statute 
    # Get the html document, construct a StatuteScraper
    #   I will need to lazily construct the formatted_data in the scraper object in the future (some re-reads might not work?) 
    # Save the link itself / way of determining if we've cached this before
    # Decide on some kind of structure to house the statutes in (folder?) with their 
        # link, title.section, datetime, html
        # JSON!
    

    # 
    def __init__(self, cache_folder: str):
        ...
        # if the cache folder doesn't exist, create it
    
    def cache_statute(self, statute_link: str) -> StatuteParser:
        ...
        # grab, cache the statute, return the parsed Statute

    def available_statutes(self): list[str]
        # read and list 