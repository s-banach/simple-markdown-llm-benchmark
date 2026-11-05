"""Questions whose answers are exact text from a table.

Every question picks rows by their content, through a key column (whose value identifies one row) or a filter condition.
"""

from collections import Counter
from collections.abc import Sequence
from itertools import cycle, islice
from random import Random
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from simple_markdown_llm_benchmark.config import QuestionKind
from simple_markdown_llm_benchmark.sampling import GenerationError, one_edit_apart, pick, randbelow
from simple_markdown_llm_benchmark.table import Table

FILTER_MATCHES = range(2, 11)
"""Allowed numbers of rows matching a filter question's condition."""


class _QuestionFields(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: int
    question: str
    answer: str


class LookupQuestion(_QuestionFields):
    """The value of `target_column` in the row whose `key_column` holds `key_value`.

    `row_index` is the 0-based index of that data row. `column_distance` is the absolute difference between the positions of the key and target columns, 1 for adjacent columns. `key_near_duplicate` is true when another value in the key column is one character edit from `key_value`.
    """

    kind: Literal["lookup"] = "lookup"
    key_column: str
    key_value: str
    target_column: str
    row_index: int
    column_distance: int
    key_near_duplicate: bool


class RowQuestion(_QuestionFields):
    """Every cell of the row whose `key_column` holds `key_value`, from left to right, joined by newlines."""

    kind: Literal["row"] = "row"
    key_column: str
    key_value: str
    row_index: int
    key_near_duplicate: bool


class FilterQuestion(_QuestionFields):
    """The values of `target_column` in every row whose `condition_column` holds `condition_value`, in table order, joined by newlines.

    `row_indices` are the 0-based indices of the matching data rows.
    """

    kind: Literal["filter"] = "filter"
    condition_column: str
    condition_value: str
    target_column: str
    row_indices: tuple[int, ...]
    column_distance: int


type Question = Annotated[LookupQuestion | RowQuestion | FilterQuestion, Field(discriminator="kind")]


def make_questions(rng: Random, table: Table, kinds: Sequence[QuestionKind], count: int) -> tuple[Question, ...]:
    """`count` questions about `table`, cycling through `kinds`."""
    asked = list(islice(cycle(kinds), count))
    keys = [i for i, column in enumerate(table) if column.is_key]
    conditions = [
        (i, value)
        for i, column in enumerate(table)
        if not column.is_key
        for value, matches in Counter(column.values).items()
        if matches in FILTER_MATCHES
    ]
    if "filter" in asked and not conditions:
        raise GenerationError(
            f"filter questions need a value that repeats in {FILTER_MATCHES.start} to {FILTER_MATCHES.stop - 1} rows of one column, and this table has none; change --rows or --columns, or drop filter from --kinds"
        )
    return tuple(
        make_question(rng, table, kind, question_id, keys, conditions) for question_id, kind in enumerate(asked)
    )


def make_question(
    rng: Random,
    table: Table,
    kind: QuestionKind,
    question_id: int,
    keys: Sequence[int],
    conditions: Sequence[tuple[int, str]],
) -> Question:
    """`keys` are the positions of key columns; `conditions` are (column position, value) pairs allowed as filter conditions."""
    match kind:
        case "lookup":
            return lookup_question(rng, table, question_id, keys)
        case "row":
            return row_question(rng, table, question_id, keys)
        case "filter":
            return filter_question(rng, table, question_id, conditions)


def lookup_question(rng: Random, table: Table, question_id: int, keys: Sequence[int]) -> LookupQuestion:
    key, row_index = _key_and_row(rng, table, keys)
    target = _other_column(rng, table, key)
    key_value = table[key].values[row_index]
    return LookupQuestion(
        question_id=question_id,
        question=f'What is the value of column "{table[target].header}" in the row where column "{table[key].header}" is "{key_value}"? Reply with the exact cell text and nothing else.',
        answer=table[target].values[row_index],
        key_column=table[key].header,
        key_value=key_value,
        target_column=table[target].header,
        row_index=row_index,
        column_distance=abs(target - key),
        key_near_duplicate=_has_near_duplicate(table[key].values, key_value),
    )


def row_question(rng: Random, table: Table, question_id: int, keys: Sequence[int]) -> RowQuestion:
    key, row_index = _key_and_row(rng, table, keys)
    key_value = table[key].values[row_index]
    return RowQuestion(
        question_id=question_id,
        question=f'List every cell of the row where column "{table[key].header}" is "{key_value}", from left to right, one value per line. Reply with those lines and nothing else.',
        answer="\n".join(column.values[row_index] for column in table),
        key_column=table[key].header,
        key_value=key_value,
        row_index=row_index,
        key_near_duplicate=_has_near_duplicate(table[key].values, key_value),
    )


def filter_question(
    rng: Random, table: Table, question_id: int, conditions: Sequence[tuple[int, str]]
) -> FilterQuestion:
    condition, condition_value = pick(rng, conditions)
    target = _other_column(rng, table, condition)
    row_indices = tuple(i for i, value in enumerate(table[condition].values) if value == condition_value)
    return FilterQuestion(
        question_id=question_id,
        question=f'List the value of column "{table[target].header}" in every row where column "{table[condition].header}" is "{condition_value}", in table order, one value per line. Reply with those lines and nothing else.',
        answer="\n".join(table[target].values[i] for i in row_indices),
        condition_column=table[condition].header,
        condition_value=condition_value,
        target_column=table[target].header,
        row_indices=row_indices,
        column_distance=abs(target - condition),
    )


def _key_and_row(rng: Random, table: Table, keys: Sequence[int]) -> tuple[int, int]:
    return pick(rng, keys), randbelow(rng, len(table[0].values))


def _other_column(rng: Random, table: Table, excluded: int) -> int:
    return pick(rng, [i for i in range(len(table)) if i != excluded])


def _has_near_duplicate(values: Sequence[str], value: str) -> bool:
    return any(one_edit_apart(value, other) for other in values)
