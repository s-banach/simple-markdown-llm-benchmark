"""A test set on disk, which any harness can run.

`<directory>/tests/<test>.txt` holds the prompt: instructions, the table, then the numbered questions.
`<directory>/keys/<test>.json` holds the `TableRecord`, with answers and question metadata, for grading.
A model's reply to `tests/<test>.txt` goes in `<answers directory>/<test>.txt`.
"""

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

from pydantic import ValidationError

from simple_markdown_llm_benchmark.benchmark import TableRecord

INSTRUCTIONS = """Answer every question after the table using only the table. Copy cell text exactly.
Reply with one block per question, in this format and nothing else:

=== Q1
<answer>
=== Q2
<answer>

Each question says what its answer holds. Put each value of a list answer on its own line."""

BLOCK_HEADER = re.compile(r"^[ \t]*=== Q(\d+)[ \t\r]*$", re.MULTILINE)


def render_prompt(record: TableRecord) -> str:
    questions = "\n\n".join(f"Q{question.question_id + 1}. {question.question}" for question in record.questions)
    return f"{INSTRUCTIONS}\n\n{record.markdown}\n\n## Questions\n\n{questions}\n"


def render_testset(records: Mapping[str, TableRecord]) -> dict[str, str]:
    """File contents by path relative to the test set directory, for records keyed by test."""
    prompts = {f"tests/{test}.txt": render_prompt(record) for test, record in records.items()}
    keys = {f"keys/{test}.json": record.model_dump_json(indent=1) + "\n" for test, record in records.items()}
    return prompts | keys


def write_testset(directory: Path, records: Mapping[str, TableRecord]) -> None:
    """Raises FileExistsError unless `directory` is absent or an empty directory, so tests from different runs never mix."""
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise FileExistsError(f"{directory} is not an empty directory; remove it or choose another --output")
    for path, text in render_testset(records).items():
        file = directory / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)


def read_keys(directory: Path) -> dict[str, TableRecord]:
    """Records keyed by test. Raises FileNotFoundError when `directory` has no keys, and ValueError naming a key that does not parse."""
    paths = sorted((directory / "keys").glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"no keys in {directory / 'keys'}")
    return {path.stem: read_key(path) for path in paths}


def read_key(path: Path) -> TableRecord:
    try:
        return TableRecord.model_validate_json(path.read_text())
    except ValidationError as error:
        raise ValueError(f"{path}: {error}") from error


def read_replies(directory: Path, tests: Iterable[str]) -> dict[str, str]:
    """The reply to each of `tests` that has a file in `directory`, keyed by test. A byte order mark at the start of a file is dropped.

    Raises NotADirectoryError when `directory` is not a directory, so a mistyped path does not grade as a model that answered nothing.
    """
    if not directory.is_dir():
        raise NotADirectoryError(f"answers directory {directory} is missing or not a directory")
    return {
        test: path.read_text(encoding="utf-8-sig") for test in tests if (path := directory / f"{test}.txt").exists()
    }


def parse_answers(text: str) -> dict[int, str]:
    """Answers keyed by `question_id`, from blocks headed `=== Q<question_id + 1>`.

    Each line is stripped and blank lines are dropped, since no cell is blank or starts or ends with a space; this keeps line endings and spaces added by a harness from failing an answer.
    """
    parts = BLOCK_HEADER.split(text)
    return {
        int(number) - 1: "\n".join(line.strip() for line in body.split("\n") if line.strip())
        for number, body in zip(parts[1::2], parts[2::2])
    }
