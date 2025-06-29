import pymupdf4llm # type: ignore
from pathlib import Path
import re


data = Path("data") / "statute" / "2024-21.pdf"


md_read = pymupdf4llm.to_markdown(data, use_glyphs=True)
with open("test_output.md", mode="w") as file:
    file.write(md_read)
# Constant= -> 21
break_point = "§21-1."
broken = md_read.split(break_point)
assert len(broken) == 3
header, toc, contents = broken

def clean_markdown_statute_text(markdown_text: str) -> str:
    # Remove footer lines like:
    # "Oklahoma Statutes - Title 21. Crimes and Punishments Page 535"
    cleaned_lines = []
    footer_pattern = re.compile(r"^Oklahoma Statutes - Title \d+\. .* Page \d+$")

    residual_md_pattern = "```"

    for line in markdown_text.splitlines():
        if footer_pattern.match(line.strip()):
            continue

        if line == residual_md_pattern:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# The result 'data' is of type List[LlamaIndexDocument]
# Every list item contains metadata and the markdown text of 1 page.

clean_contents = clean_markdown_statute_text(contents)
with open("test_output_clean.md", mode="w") as file:
    file.write(clean_contents)



STATUTE_HEADER_RE = re.compile(r"^§[^\s]+-[^\s]+\.",  re.MULTILINE)
# STATUTE_HEADER_RE = re.compile(r"^§\d+[A-Z]?(?:\.\d+)?-[\dA-Za-z\.]+", re.MULTILINE) # worse


def split_statutes_by_header(md_text: str):
    matches = list(STATUTE_HEADER_RE.finditer(md_text))
    statutes = []

    for i, match in enumerate(matches):
        
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)

        header_line = match.group().strip()
        if not header_line.startswith("§"): 
            print("FAILURE")
            print(match.group())
            print(header_line)
        body = md_text[start:end].strip()

        if header_line == "2-503.":
            print("FOUND IT")
            if header_line.startswith("§"): 
                print("repr(header_line):", repr(header_line))
                print("ord(header_line[0]):", ord(header_line[0]))
                print("header_line:", header_line)
                print("And it starts with stat.")
        
        statutes.append((header_line, body))

    return statutes


res = split_statutes_by_header(clean_contents)
split_toc = split_statutes_by_header(toc)

split_toc
print(len(split_toc)) # 1492
print(len(res)) # 1497

print(split_toc[15][0]) # §21-13.1v2.
print(res[15][0]) # 21-13.

# left off on random things like 2-503. getting caught. Somehow the statute symbol isn't included here? 
print(split_toc[39][0]) # §21-20N.
print(res[39][0]) # 2-503. <--??? 

# for r in res:
#     print()
#     print()
#     print()
#     print()
#     print(r[1])