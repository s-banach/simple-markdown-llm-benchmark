"""Benchmark v1: the settings on which Claude Sonnet and Haiku failed most often, written as a test set for any harness.

Every table has 12,000 cells, and each prompt about 140,000 characters, which Sonnet and Haiku read within a 200k-token context. Each shape provokes a different failure:

- 1000 x 12: models leave matching rows out of filter answers.
- 300 x 40: the same, less often.
- 100 x 120: the 40 order-table columns appear three times with suffixed headers, and models take a same-named column from another block (`invoice_number_3` for `invoice_number`) or shift cells when copying a row.

Each shape comes with plausible and gibberish content, so a model cannot tell columns apart by the look of their cells in half the tests.
"""

import sys
from pathlib import Path
from typing import get_args

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import CliApp, SettingsConfigDict

from simple_markdown_llm_benchmark.benchmark import TableRecord, make_record
from simple_markdown_llm_benchmark.config import BenchmarkConfig, Content, setting_name
from simple_markdown_llm_benchmark.testset import write_testset

SHAPES = ((1000, 12), (300, 40), (100, 120))
"""Rows and columns of each shape."""
QUESTIONS = 30
"""Per table, cycling through lookup, row and filter."""
NEAR_DUPLICATES = 0.2


class BenchmarkV1Options(BaseModel):
    """Write benchmark v1: tables of 12,000 cells in 3 shapes (1000 x 12, 300 x 40, 100 x 120) and 2 contents (plausible, gibberish), with 30 questions each, as plaintext prompts plus answer keys."""

    model_config = SettingsConfigDict(
        frozen=True, cli_kebab_case=True, cli_prog_name="simple-markdown-llm-benchmark-v1"
    )

    seed: int = Field(
        0,
        description="Random seed. Seed 0 is the reference test set; other seeds draw new tables of the same settings.",
    )
    tables: int = Field(
        3,
        ge=1,
        description="Tables per setting. A table does not depend on this value, so raising it extends the test set.",
    )
    output: Path | None = Field(
        None, description="Directory to write, which must be absent or empty. Defaults to benchmark_v1_seed<seed>."
    )


def settings(seed: int) -> tuple[BenchmarkConfig, ...]:
    """One config per shape and content."""
    return tuple(
        BenchmarkConfig(
            rows=rows,
            columns=columns,
            content=content,
            near_duplicates=NEAR_DUPLICATES,
            questions=QUESTIONS,
            seed=seed,
        )
        for rows, columns in SHAPES
        for content in get_args(Content)
    )


def benchmark_v1(seed: int, tables: int) -> dict[str, TableRecord]:
    """`tables` records per setting, keyed by test `<setting>_<index>`."""
    configs = settings(seed)
    return {
        f"{setting_name(config)}_{index}": make_record(config, index * len(configs) + position)
        for position, config in enumerate(configs)
        for index in range(tables)
    }


def main() -> None:
    try:
        options = CliApp.run(BenchmarkV1Options)
        directory = Path(f"benchmark_v1_seed{options.seed}") if options.output is None else options.output
        records = benchmark_v1(options.seed, options.tables)
        write_testset(directory, records)
    except (ValidationError, FileExistsError) as error:
        sys.exit(f"error: {error}")
    questions = sum(len(record.questions) for record in records.values())
    print(f"wrote {len(records)} tests with {questions} questions to {directory}")


if __name__ == "__main__":
    main()
