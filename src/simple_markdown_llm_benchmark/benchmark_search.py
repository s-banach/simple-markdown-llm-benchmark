"""The search benchmark: find every row whose complaint contains a phrase, in tables of real consumer complaints.

Each table has an order_id column, six other order-table columns, and a complaint column of CFPB consumer complaint narratives of 530 to 1522 characters. Each question gives a phrase of three words found in 2 to 10 complaints and asks for the order_id of every row whose complaint contains it.

Models copy the complaints verbatim almost perfectly; they fail by leaving matching rows out. In tests of Claude Sonnet with thinking on 500-row tables, almost no answer listed a wrong row, but answers held about half of the matching rows. Tables of 100, 250 and 500 rows show how a model's score falls as tables grow.
"""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from simple_markdown_llm_benchmark.config import BenchmarkConfig
from simple_markdown_llm_benchmark.preset import PresetOptions, run_preset
from simple_markdown_llm_benchmark.prose import narratives


class BenchmarkSearchOptions(PresetOptions):
    """Write the search benchmark: tables of orders, each with a consumer complaint, and questions asking for the order_id of every row whose complaint contains a phrase, as plaintext prompts plus answer keys."""

    model_config = SettingsConfigDict(cli_prog_name="simple-markdown-llm-benchmark-search")

    rows: tuple[int, ...] = Field(
        (100, 250, 500),
        min_length=1,
        description=f"Table sizes in rows, comma-separated, each at most {len(narratives('long'))}. A prompt takes about 1,150 characters, or about 420 Claude tokens, per row.",
    )
    questions: int = Field(10, ge=1, description="Questions per table.")


def settings(options: BenchmarkSearchOptions) -> tuple[BenchmarkConfig, ...]:
    """One config per table size."""
    return tuple(
        BenchmarkConfig(
            rows=rows, columns=8, prose_columns=1, questions=options.questions, kinds=("search",), seed=options.seed
        )
        for rows in options.rows
    )


def main() -> None:
    run_preset("benchmark_search", BenchmarkSearchOptions, settings)


if __name__ == "__main__":
    main()
