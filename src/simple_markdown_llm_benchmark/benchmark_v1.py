"""Benchmark v1: the settings on which Claude Sonnet and Haiku failed most often, written as a test set for any harness.

Every table has 12,000 cells, and each prompt about 140,000 characters, which Sonnet and Haiku read within a 200k-token context. Each shape provokes a different failure:

- 1000 x 12: models leave matching rows out of filter answers.
- 300 x 40: the same, less often.
- 100 x 120: the 40 order-table columns appear three times with suffixed headers, and models take a same-named column from another block (`invoice_number_3` for `invoice_number`) or shift cells when copying a row.
"""

from pydantic_settings import SettingsConfigDict

from simple_markdown_llm_benchmark.config import BenchmarkConfig
from simple_markdown_llm_benchmark.preset import PresetOptions, run_preset

SHAPES = ((1000, 12), (300, 40), (100, 120))
"""Rows and columns of each shape."""
QUESTIONS = 30
"""Per table, cycling through lookup, row and filter."""
NEAR_DUPLICATES = 0.2


class BenchmarkV1Options(PresetOptions):
    """Write benchmark v1: tables of 12,000 cells in 3 shapes (1000 x 12, 300 x 40, 100 x 120), with 30 questions each, as plaintext prompts plus answer keys."""

    model_config = SettingsConfigDict(cli_prog_name="simple-markdown-llm-benchmark-v1")


def settings(options: BenchmarkV1Options) -> tuple[BenchmarkConfig, ...]:
    """One config per shape."""
    return tuple(
        BenchmarkConfig(
            rows=rows, columns=columns, near_duplicates=NEAR_DUPLICATES, questions=QUESTIONS, seed=options.seed
        )
        for rows, columns in SHAPES
    )


def main() -> None:
    run_preset("benchmark_v1", BenchmarkV1Options, settings)


if __name__ == "__main__":
    main()
