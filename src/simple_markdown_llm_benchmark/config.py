from typing import Literal, get_args

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from simple_markdown_llm_benchmark.columns import ORDER_COLUMNS

Content = Literal["plausible", "gibberish"]
QuestionKind = Literal["lookup", "row", "filter"]


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
    pad: bool = Field(False, description="Pad cells with spaces so columns line up.")
    tables: int = Field(1, ge=1, description="Tables to generate, one JSON line each.")
    questions: int = Field(20, ge=1, description="Questions per table.")
    kinds: tuple[QuestionKind, ...] = Field(
        get_args(QuestionKind), min_length=1, description="Question kinds, assigned to questions in turn."
    )
    seed: int = Field(0, description="Random seed.")


def setting_name(config: BenchmarkConfig) -> str:
    """Names the table settings that a test set varies, such as `1000x12_plausible`."""
    return f"{config.rows}x{config.columns}_{config.content}" + ("_padded" if config.pad else "")
