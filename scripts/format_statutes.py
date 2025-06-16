import json
from pathlib import Path
from typing import Union

from nlp.statute_formatter import StatuteFormatter


def parse_statute_folder(
    input_folder: Union[str, Path],
    output_folder: Union[str, Path],
    model: str,
    context_length: int,
    verbose=False,
):
    formatter = StatuteFormatter(
        model=model, context_length=context_length, proofread=True, verbose=verbose
    )

    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    if not input_folder.exists() or not input_folder.is_dir():
        raise ValueError(f"Invalid input folder path: {input_folder}")

    parsed_results = {}

    for file_path in input_folder.glob("*.json"):
        output_path = output_folder / file_path.name

        if output_path.exists():
            print(f"Skipping {file_path.name}, already parsed.")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_texts = data.get("raw_texts")
        if not raw_texts or not isinstance(raw_texts, list):
            raise ValueError(f"No valid 'raw_texts' in {file_path.name}")
        
        print()
        print()
        print(f"Processing {file_path.name}...")

        result = formatter.process_statute(raw_statute=raw_texts)

        with open(output_path, "w", encoding="utf-8") as out_f:
            out_f.write(json.dumps(result, indent=2, ensure_ascii=False))

        parsed_results[file_path.name] = result

    return parsed_results


if __name__ == "__main__":
    parse_statute_folder(
        input_folder=Path("data") / "statute_cache",
        output_folder=Path("data") / "formatted_statutes",
        model="qwen3:8b",
        context_length=16384,
        verbose=True,
    )
