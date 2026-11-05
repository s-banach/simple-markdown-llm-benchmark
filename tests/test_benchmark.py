from itertools import cycle, islice

import pytest

from simple_markdown_llm_benchmark import (
    BenchmarkConfig,
    FilterQuestion,
    GenerationError,
    LookupQuestion,
    RowQuestion,
    generate,
)
from simple_markdown_llm_benchmark.columns import ORDER_COLUMNS
from simple_markdown_llm_benchmark.config import Content
from simple_markdown_llm_benchmark.sampling import one_edit_apart


def parse(markdown: str) -> tuple[list[str], list[list[str]]]:
    """Headers and data rows of a rendered table, with padding stripped."""
    lines = markdown.split("\n")
    cells = [[cell.strip() for cell in line.removeprefix("| ").removesuffix(" |").split(" | ")] for line in lines]
    assert all(set(cell) == {"-"} for cell in cells[1])
    return cells[0], cells[2:]


def column(headers: list[str], data_rows: list[list[str]], header: str) -> list[str]:
    return [row[headers.index(header)] for row in data_rows]


@pytest.mark.parametrize(
    "config",
    [
        BenchmarkConfig(rows=150, columns=50, near_duplicates=0.3, tables=2, questions=30),
        BenchmarkConfig(rows=150, columns=50, near_duplicates=0.3, tables=2, questions=30, pad=True),
        BenchmarkConfig(rows=150, columns=50, near_duplicates=0.3, tables=2, questions=30, content="gibberish"),
        BenchmarkConfig(rows=7, near_duplicates=1, questions=10, kinds=("lookup", "row")),
        BenchmarkConfig(rows=1, columns=2, questions=1),
    ],
)
def test_every_answer_matches_the_rendered_table(config: BenchmarkConfig) -> None:
    for record in generate(config):
        headers, data_rows = parse(record.markdown)
        assert len(data_rows) == config.rows
        assert len(set(headers)) == config.columns
        assert all(len(row) == config.columns for row in data_rows)
        assert [question.kind for question in record.questions] == list(islice(cycle(config.kinds), config.questions))
        for question in record.questions:
            match question:
                case LookupQuestion():
                    keys = column(headers, data_rows, question.key_column)
                    assert [i for i, value in enumerate(keys) if value == question.key_value] == [question.row_index]
                    assert column(headers, data_rows, question.target_column)[question.row_index] == question.answer
                    assert question.key_column != question.target_column
                case RowQuestion():
                    keys = column(headers, data_rows, question.key_column)
                    assert [i for i, value in enumerate(keys) if value == question.key_value] == [question.row_index]
                    assert question.answer == "\n".join(data_rows[question.row_index])
                case FilterQuestion():
                    conditions = column(headers, data_rows, question.condition_column)
                    matches = [i for i, value in enumerate(conditions) if value == question.condition_value]
                    assert list(question.row_indices) == matches
                    assert 2 <= len(matches) <= 10
                    targets = column(headers, data_rows, question.target_column)
                    assert question.answer == "\n".join(targets[i] for i in matches)


def key_positions(columns: int) -> list[int]:
    """Positions of the columns built as keys in a table of `columns` columns."""
    return [i for i in range(columns) if ORDER_COLUMNS[i % len(ORDER_COLUMNS)].distinct is None]


@pytest.mark.parametrize("content", ["plausible", "gibberish"])
def test_questions_identify_rows_only_by_columns_built_as_keys(content: Content) -> None:
    """In small tables, columns such as quantity can be all distinct by chance; they must not serve as keys."""
    config = BenchmarkConfig(rows=6, columns=40, content=content, questions=60, kinds=("lookup", "row"))
    record = next(generate(config))
    headers, _ = parse(record.markdown)
    key_headers = {headers[i] for i in key_positions(config.columns)}
    for question in record.questions:
        assert isinstance(question, LookupQuestion | RowQuestion)
        assert question.key_column in key_headers


def test_equal_configs_give_equal_output_and_seeds_differ() -> None:
    config = BenchmarkConfig(rows=50, tables=3, questions=5)
    assert list(generate(config)) == list(generate(config))
    assert list(generate(config)) != list(generate(BenchmarkConfig(rows=50, tables=3, questions=5, seed=1)))


@pytest.mark.parametrize("content", ["plausible", "gibberish"])
def test_near_duplicates_cover_the_requested_fraction_of_key_values(content: Content) -> None:
    config = BenchmarkConfig(rows=200, columns=40, content=content, near_duplicates=0.5, questions=1, kinds=("lookup",))
    _, data_rows = parse(next(generate(config)).markdown)
    key_columns = [[row[i] for row in data_rows] for i in key_positions(config.columns)]
    for values in key_columns:
        with_near_duplicate = sum(any(one_edit_apart(value, other) for other in values) for value in values)
        assert with_near_duplicate >= 0.5 * len(values)


@pytest.mark.parametrize(
    "config",
    [
        BenchmarkConfig(rows=100, content="gibberish", cell_length=1),
        BenchmarkConfig(columns=2, kinds=("filter",)),
    ],
)
def test_impossible_configs_raise(config: BenchmarkConfig) -> None:
    with pytest.raises(GenerationError):
        list(generate(config))
