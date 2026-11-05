"""A test set on disk, which any harness can run.

`<directory>/tests/<test>.txt` holds the prompt: instructions, the table, then the numbered questions.
`<directory>/keys/<test>.json` holds the `TableRecord`, with answers and question metadata, for grading.
A model's reply to `tests/<test>.txt` goes in `<answers directory>/<test>.txt`.
"""

import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import CliApp, CliPositionalArg, SettingsConfigDict

from simple_markdown_llm_benchmark.benchmark import TableRecord
from simple_markdown_llm_benchmark.config import setting_name

INSTRUCTIONS = """Answer every question after the table using only the table. Copy cell text exactly.
Reply with one block per question, in this format and nothing else:

=== Q1
<answer>
=== Q2
<answer>

Each question says what its answer holds. Put each value of a list answer on its own line."""

PROSE_INSTRUCTIONS = (
    "Some cells hold paragraphs separated by <br><br>. Copy <br> tags as they appear, and keep each cell on one line."
)

BLOCK_HEADER = re.compile(r"^[ \t]*=== Q(\d+)[ \t\r]*$", re.MULTILINE)


class TestSetOptions(BaseModel):
    """Write tables from simple-markdown-llm-benchmark as a test set: a prompt in tests/<test>.txt and an answer key in keys/<test>.json for each table, where <test> is <setting>_<table_id>, such as 80x8_plausible_prose2_0."""

    model_config = SettingsConfigDict(
        frozen=True, cli_kebab_case=True, cli_prog_name="simple-markdown-llm-benchmark-testset"
    )

    records: CliPositionalArg[Path] = Field(description="JSON lines written by simple-markdown-llm-benchmark.")
    output: CliPositionalArg[Path] = Field(description="Directory to write, which must be absent or empty.")


def render_prompt(record: TableRecord) -> str:
    instructions = f"{INSTRUCTIONS}\n{PROSE_INSTRUCTIONS}" if record.config.prose_columns else INSTRUCTIONS
    questions = "\n\n".join(f"Q{question.question_id + 1}. {question.question}" for question in record.questions)
    return f"{instructions}\n\n{record.markdown}\n\n## Questions\n\n{questions}\n"


def records_by_test(records: Sequence[TableRecord]) -> dict[str, TableRecord]:
    """Records keyed by test `<setting>_<table_id>`. Raises ValueError when two records get the same test name."""
    tests = [f"{setting_name(record.config)}_{record.table_id}" for record in records]
    repeated = [test for test, count in Counter(tests).items() if count > 1]
    if repeated:
        raise ValueError(f"several tables would be named {', '.join(repeated)}; write them to separate test sets")
    return dict(zip(tests, records, strict=True))


def render_testset(records: Mapping[str, TableRecord]) -> dict[str, str]:
    """File contents by path relative to the test set directory, for records keyed by test."""
    prompts = {f"tests/{test}.txt": render_prompt(record) for test, record in records.items()}
    keys = {f"keys/{test}.json": record.model_dump_json(indent=1) + "\n" for test, record in records.items()}
    return prompts | keys


def write_testset(directory: Path, records: Mapping[str, TableRecord]) -> None:
    """Raises FileExistsError unless `directory` is absent or an empty directory, so tests from different runs never mix."""
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise FileExistsError(f"{directory} is not an empty directory; remove it or choose another directory")
    for path, text in render_testset(records).items():
        file = directory / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")


def read_keys(directory: Path) -> dict[str, TableRecord]:
    """Records keyed by test. Raises FileNotFoundError when `directory` has no keys, and ValueError naming a key that does not parse."""
    paths = sorted((directory / "keys").glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"no keys in {directory / 'keys'}")
    return {path.stem: read_key(path) for path in paths}


def read_key(path: Path) -> TableRecord:
    try:
        return TableRecord.model_validate_json(path.read_text(encoding="utf-8"))
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


def main() -> None:
    try:
        options = CliApp.run(TestSetOptions)
        lines = options.records.read_text(encoding="utf-8").splitlines()
        tests = records_by_test([TableRecord.model_validate_json(line) for line in lines])
        write_testset(options.output, tests)
    except (ValueError, OSError) as error:
        sys.exit(f"error: {error}")
    print(f"wrote {len(tests)} tests to {options.output}")


if __name__ == "__main__":
    main()
