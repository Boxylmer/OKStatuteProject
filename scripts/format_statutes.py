import os
import json
from pathlib import Path
from typing import Union

from nlp.statute_extractor import format_raw_statute

def parse_statute_folder(
    input_folder: Union[str, Path],
    output_folder: Union[str, Path],
    model="gemma3:4b-it-qat",
    context_length=16384,
    verbose=False
):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    if not input_folder.exists() or not input_folder.is_dir():
        raise ValueError(f"Invalid input folder path: {input_folder}")

    parsed_results = {}
    errors = {} # type: ignore

    for file_path in input_folder.glob("*.json"):
        output_path = output_folder / file_path.name

        if output_path.exists():
            print(f"Skipping {file_path.name}, already parsed.")
            continue

        # try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_texts = data.get("raw_texts")
        if not raw_texts or not isinstance(raw_texts, list):
            raise ValueError(f"No valid 'raw_texts' in {file_path.name}")

        print(f"Processing {file_path.name}...")

        result = format_raw_statute(
            statute=raw_texts,
            model=model,
            context_length=context_length,
            verbose=verbose,
        )

        with open(output_path, "w", encoding="utf-8") as out_f:
            out_f.write(json.dumps(result, indent=2, ensure_ascii=False))

        parsed_results[file_path.name] = result

        # except Exception as e:
        #     print(f"Error parsing {file_path.name}: {e}")
        #     errors[file_path.name] = str(e)

    print(f"\nFinished processing {len(parsed_results)} statutes with {len(errors)} errors.")
    return parsed_results, errors


if __name__ == "__main__":
    parse_statute_folder(
        input_folder=Path("data") / "statute_cache",
        output_folder=Path("data") / "formatted_statutes",
        verbose=True,
        # model="qwen3:8b"
        model="granite3.3:8b"
    )
