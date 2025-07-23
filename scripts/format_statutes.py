from collections import Counter
import json
from pathlib import Path
from typing import Union


from deprecated.statute_formatter import StatuteFormatter, StatutePostprocessor


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
    
    files = list(input_folder.glob("*.json"))

    for i, file_path in enumerate(files):
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
        print(f"Processing {file_path.name} ({i}/{len(files)})...")
        try:
            result = formatter.process_statute_line_by_line(raw_statute=raw_texts)

            with open(output_path, "w", encoding="utf-8") as out_f:
                out_f.write(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print("--------------------------------FAILED--------------------------------")
            print(e)
            print("----------------------------------------------------------------------")
            

def postprocess_statutes(
    input_folder: Union[str, Path],
    output_folder: Union[str, Path],
    verbose=False,
):
    formatter = StatutePostprocessor()

    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    unlabeled_lengths = []

    files = list(input_folder.glob("*.json"))

    for i, file_path in enumerate(files):
        output_path = output_folder / file_path.name

        if output_path.exists():
            print(f"Skipping {file_path.name}, already parsed.")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print()
        print()
        print(f"Postprocessing {file_path.name} ({i}/{len(files)})...")

        unlabeled_lengths.extend(formatter.log_unlabeled_line_lengths(parsed_statute=data))

        # with open(output_path, "w", encoding="utf-8") as out_f:
        #     out_f.write(json.dumps(result, indent=2, ensure_ascii=False))
    
    counted_lengths = Counter(unlabeled_lengths)
    for length in sorted(counted_lengths):
        print(f"{str(length).rjust(5)} → {str(counted_lengths[length]).rjust(5)}")


if __name__ == "__main__":
    parse_statute_folder(
        input_folder=Path("data") / "statute_cache",
        output_folder=Path("data") / "formatted_statutes",
        model="qwen3:14b",
        context_length=4096,
        verbose=True,
    )
    # postprocess_statutes(
    #     input_folder=Path("data") / "formatted_statutes",
    #     output_folder =Path("data") / "postprocessed_statutes",
    #     verbose=True,
    # )
