from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import SettingsConfigDict

from simple_markdown_llm_benchmark.columns import ORDER_COLUMNS

Content = Literal["plausible", "gibberish"]
QuestionKind = Literal["lookup", "quote", "row", "filter"]
ProseLength = Literal["long", "short"]


class BenchmarkConfig(BaseModel):
    """Generate markdown tables and questions with exact-text answers, one JSON line per table. Equal settings give equal output."""

    model_config = SettingsConfigDict(
        frozen=True, cli_kebab_case=True, cli_implicit_flags=True, cli_prog_name="simple-markdown-llm-benchmark"
    )

    rows: int = Field(200, ge=1, description="Data rows per table.")
    columns: int = Field(
        10,
        ge=2,
        description=f"Columns per table. Beyond {len(ORDER_COLUMNS)}, the order-table columns repeat with suffixed headers (status_2).",
    )
    content: Content = Field(
        "plausible",
        description="plausible: an order table of names, cities, products, prices and dates. gibberish: the same column layout with random lowercase headers and cells.",
    )
    cell_length: int = Field(8, ge=1, description="Characters in each gibberish header and cell.")
    near_duplicates: float = Field(
        0.0,
        ge=0,
        le=1,
        description="Fraction of values in each key column (a column built to give every row a different value, such as order_id) that have a near duplicate: another value one substituted or swapped character away.",
    )
    # Benchmark v1 answer keys, pinned by test_benchmark_v1_seed_0_is_unchanged, have no prose fields,
    # so each prose field is left out of serialized configs at its default.
    prose_columns: int = Field(
        0,
        ge=0,
        exclude_if=lambda prose_columns: prose_columns == 0,
        description="How many of the columns, placed last, hold prose: passages of two or more paragraphs joined by <br><br>. Plausible prose comes from CFPB consumer complaints; gibberish prose is random words in sentences.",
    )
    prose_length: ProseLength = Field(
        "long",
        exclude_if=lambda prose_length: prose_length == "long",
        description="long: complaints of 530 to 1522 characters. short: the same complaints cut to at most 400 characters by deleting whole sentences. Gibberish prose copies the paragraph word counts of the chosen complaints.",
    )
    pad: bool = Field(False, description="Pad cells with spaces so columns line up.")
    tables: int = Field(1, ge=1, description="Tables to generate, one JSON line each.")
    questions: int = Field(20, ge=1, description="Questions per table.")
    kinds: tuple[QuestionKind, ...] = Field(
        ("lookup", "row", "filter"),
        min_length=1,
        description="Question kinds, assigned to questions in turn. lookup asks for one cell, quote for one prose cell, row for every cell of a row, and filter for a column's values in every row that matches a condition.",
    )
    seed: int = Field(0, description="Random seed.")

    @model_validator(mode="after")
    def keep_a_key_column(self) -> Self:
        if self.prose_columns >= self.columns:
            raise ValueError("--prose-columns must be below --columns, so the table keeps its key column")
        return self

    @model_validator(mode="after")
    def give_prose_length_only_with_prose(self) -> Self:
        if self.prose_length == "short" and not self.prose_columns:
            raise ValueError("--prose-length short needs --prose-columns")
        return self


def setting_name(config: BenchmarkConfig) -> str:
    """Names the table settings that a test set varies, such as `1000x12_plausible` or `80x8_gibberish_prose2_short`."""
    return (
        f"{config.rows}x{config.columns}_{config.content}"
        + (f"_prose{config.prose_columns}" if config.prose_columns else "")
        + ("_short" if config.prose_length == "short" else "")
        + ("_padded" if config.pad else "")
    )
