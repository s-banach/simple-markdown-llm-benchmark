import re
from itertools import cycle, groupby, islice
from operator import itemgetter
from typing import get_args

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
from simple_markdown_llm_benchmark.config import Content, ProseLength
from simple_markdown_llm_benchmark.prose import PARAGRAPH_BREAK, narratives
from simple_markdown_llm_benchmark.sampling import one_edit_apart
from simple_markdown_llm_benchmark.table import Row, parse_markdown

SENTENCE_END = re.compile(r"(?<=[.!?]) (?=[A-Z])")
"""Where the narratives were split into sentences when the short texts were chosen."""


def column(headers: Row, data_rows: tuple[Row, ...], header: str) -> list[str]:
    return [row[headers.index(header)] for row in data_rows]


@pytest.mark.parametrize(
    "config",
    [
        BenchmarkConfig(rows=150, columns=50, near_duplicates=0.3, tables=2, questions=30),
        BenchmarkConfig(rows=150, columns=50, near_duplicates=0.3, tables=2, questions=30, pad=True),
        BenchmarkConfig(rows=150, columns=50, near_duplicates=0.3, tables=2, questions=30, content="gibberish"),
        BenchmarkConfig(rows=7, near_duplicates=1, questions=10, kinds=("lookup", "row")),
        BenchmarkConfig(rows=1, columns=2, questions=1),
        BenchmarkConfig(rows=60, columns=8, prose_columns=2, questions=40, kinds=("lookup", "quote", "row", "filter")),
        BenchmarkConfig(
            rows=60,
            columns=8,
            prose_columns=2,
            questions=40,
            kinds=("lookup", "quote", "row", "filter"),
            content="gibberish",
        ),
        BenchmarkConfig(
            rows=60, columns=8, prose_columns=2, prose_length="short", questions=20, kinds=("quote", "row")
        ),
    ],
)
def test_every_answer_matches_the_rendered_table(config: BenchmarkConfig) -> None:
    for record in generate(config):
        headers, data_rows = parse_markdown(record.markdown)
        prose_headers = headers[config.columns - config.prose_columns :]
        assert set(record.markdown.split("\n")[1]) == set("|- ")
        assert len(data_rows) == config.rows
        assert len(set(headers)) == config.columns
        assert all(len(row) == config.columns for row in data_rows)
        assert all(PARAGRAPH_BREAK in cell for header in prose_headers for cell in column(headers, data_rows, header))
        assert [question.kind for question in record.questions] == list(islice(cycle(config.kinds), config.questions))
        for question in record.questions:
            match question:
                case LookupQuestion():
                    keys = column(headers, data_rows, question.key_column)
                    assert [i for i, value in enumerate(keys) if value == question.key_value] == [question.row_index]
                    assert column(headers, data_rows, question.target_column)[question.row_index] == question.answer
                    assert question.key_column != question.target_column
                    assert (question.target_column in prose_headers) == (question.kind == "quote")
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
                    assert question.target_column not in prose_headers


def key_positions(columns: int) -> list[int]:
    """Positions of the columns built as keys in a table of `columns` columns."""
    return [i for i in range(columns) if ORDER_COLUMNS[i % len(ORDER_COLUMNS)].distinct is None]


@pytest.mark.parametrize("content", ["plausible", "gibberish"])
def test_questions_identify_rows_only_by_columns_built_as_keys(content: Content) -> None:
    """In small tables, columns such as quantity can be all distinct by chance; they must not serve as keys."""
    config = BenchmarkConfig(rows=6, columns=40, content=content, questions=60, kinds=("lookup", "row"))
    record = next(generate(config))
    headers, _ = parse_markdown(record.markdown)
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
    _, data_rows = parse_markdown(next(generate(config)).markdown)
    key_columns = [[row[i] for row in data_rows] for i in key_positions(config.columns)]
    for values in key_columns:
        with_near_duplicate = sum(any(one_edit_apart(value, other) for other in values) for value in values)
        assert with_near_duplicate >= 0.5 * len(values)


@pytest.mark.parametrize(
    "config",
    [
        BenchmarkConfig(rows=100, content="gibberish", cell_length=1),
        BenchmarkConfig(columns=2, kinds=("filter",)),
        BenchmarkConfig(kinds=("quote",)),
        BenchmarkConfig(columns=3, prose_columns=2, kinds=("lookup",)),
        BenchmarkConfig(rows=len(narratives("long")) // 2 + 1, columns=3, prose_columns=2, kinds=("quote",)),
    ],
)
def test_impossible_configs_raise(config: BenchmarkConfig) -> None:
    with pytest.raises(GenerationError):
        list(generate(config))


@pytest.mark.parametrize("length", get_args(ProseLength))
def test_narratives_fit_table_cells(length: ProseLength) -> None:
    texts = [narrative.text for narrative in narratives(length)]
    assert len(set(texts)) == len(texts)
    for text in texts:
        paragraphs = text.split(PARAGRAPH_BREAK)
        assert len(paragraphs) >= 2
        assert all(paragraph and paragraph == paragraph.strip() for paragraph in paragraphs)
        assert not set("|\\<\n") & set("".join(paragraphs))


def test_short_narratives_delete_whole_sentences_of_long_ones() -> None:
    """Each short text is its long text with sentences deleted: kept sentences keep their order, a space joins two from one long paragraph, and a paragraph break joins two from different ones."""
    long_texts = {narrative.complaint_id: narrative.text for narrative in narratives("long")}
    for narrative in narratives("short"):
        assert len(narrative.text) <= 400
        remaining = iter(sentences(long_texts[narrative.complaint_id]))
        kept = [next(found for found in remaining if found[1] == sentence) for _, sentence in sentences(narrative.text)]
        assert (
            PARAGRAPH_BREAK.join(
                " ".join(sentence for _, sentence in group) for _, group in groupby(kept, key=itemgetter(0))
            )
            == narrative.text
        )


def sentences(passage: str) -> list[tuple[int, str]]:
    """Each sentence of `passage`, with the index of its paragraph."""
    return [
        (index, sentence)
        for index, paragraph in enumerate(passage.split(PARAGRAPH_BREAK))
        for sentence in SENTENCE_END.split(paragraph)
    ]
