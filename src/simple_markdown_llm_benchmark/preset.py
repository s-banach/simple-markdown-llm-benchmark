"""Fixed test sets: a list of settings, written as a test set for any harness."""

import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import CliApp, SettingsConfigDict

from simple_markdown_llm_benchmark.benchmark import TableRecord, make_record
from simple_markdown_llm_benchmark.config import BenchmarkConfig
from simple_markdown_llm_benchmark.sampling import GenerationError
from simple_markdown_llm_benchmark.testset import records_by_test, write_testset


class PresetOptions(BaseModel):
    model_config = SettingsConfigDict(frozen=True, cli_kebab_case=True)

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
        None,
        description="Directory to write, which must be absent or empty. Defaults to benchmark_v1_seed<seed> for simple-markdown-llm-benchmark-v1 and benchmark_search_seed<seed> for simple-markdown-llm-benchmark-search.",
    )


def records_by_setting(configs: Sequence[BenchmarkConfig], tables: int) -> dict[str, TableRecord]:
    """Tables 0 to `tables - 1` of each config, keyed by test. Raises ValueError when two configs share a setting name."""
    return records_by_test([make_record(config, table_id) for config in configs for table_id in range(tables)])


def run_preset[Options: PresetOptions](
    name: str, options_class: type[Options], settings: Callable[[Options], Sequence[BenchmarkConfig]]
) -> None:
    """Parse `options_class` from the command line and write the test set of `settings(options)` to `<name>_seed<seed>`, or to `--output`."""
    try:
        options = CliApp.run(options_class)
        directory = Path(f"{name}_seed{options.seed}") if options.output is None else options.output
        records = records_by_setting(settings(options), options.tables)
        write_testset(directory, records)
    except (ValueError, GenerationError, FileExistsError) as error:
        sys.exit(f"error: {error}")
    questions = sum(len(record.questions) for record in records.values())
    print(f"wrote {len(records)} tests with {questions} questions to {directory}")
