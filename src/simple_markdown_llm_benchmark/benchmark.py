from collections.abc import Iterator
from random import Random

from pydantic import BaseModel, ConfigDict

from simple_markdown_llm_benchmark.config import BenchmarkConfig, setting_name
from simple_markdown_llm_benchmark.questions import Question, make_questions
from simple_markdown_llm_benchmark.table import generate_table, render_markdown


class TableRecord(BaseModel):
    """One table in markdown and the questions about it."""

    model_config = ConfigDict(frozen=True)

    table_id: int
    config: BenchmarkConfig
    markdown: str
    questions: tuple[Question, ...]


def generate(config: BenchmarkConfig) -> Iterator[TableRecord]:
    return (make_record(config, table_id) for table_id in range(config.tables))


def make_record(config: BenchmarkConfig, table_id: int) -> TableRecord:
    """Table `table_id` of the benchmark. Its random draws depend only on the seed, the setting name and `table_id`, so any one table can be regenerated alone, and adding or removing other settings leaves it unchanged."""
    rng = Random(f"{config.seed}:{setting_name(config)}:{table_id}")
    table = generate_table(rng, config)
    return TableRecord(
        table_id=table_id,
        config=config,
        markdown=render_markdown(table, config.pad),
        questions=make_questions(rng, table, config.kinds, config.questions),
    )
