from pathlib import Path

import fitz  # type: ignore


def parse_statute_doc(pdf_path: Path, x_min=86, x_max=521):
    # margins =
    pdf = fitz.open(pdf_path)
    lines = []
    for page in pdf:
        blocks = page.get_text("blocks")
        if page.number == 31 or page.number == 32 or page.number == 33:
            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                if x_min <= x0 <= x_max and x_min <= x1 <= x_max:
                    for line in text.split("\n"):
                        line = line.strip()
                        if line:
                            print(line)
                            lines.append(line)
        # return
        # print(page.get_text())



if __name__ == "__main__":
    data = Path("data") / "statute" / "2024-21.pdf"

    parse_statute_doc(data)
