"""Questions whose answers are exact text from a table.

Every question picks rows by their content, through a key column (whose value identifies one row), a filter condition, or a phrase in a prose cell.
"""

import re
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import cycle, islice
from random import Random
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from simple_markdown_llm_benchmark.config import QuestionKind
from simple_markdown_llm_benchmark.prose import PARAGRAPH_BREAK
from simple_markdown_llm_benchmark.sampling import GenerationError, one_edit_apart, pick, randbelow
from simple_markdown_llm_benchmark.table import ColumnRole, Table

MATCHING_ROWS = range(2, 11)
"""Allowed numbers of rows matching a filter question's condition or a search question's phrase."""
PHRASE = re.compile(r"[A-Za-z]+ [A-Za-z]+ [A-Za-z]+")
"""A search phrase: three words of letters only."""
SEPARATOR = re.compile(r"[\s.,;:!?()\"]+")
"""Spaces and punctuation that a reader may skip between the words of a phrase."""
WORD_EDGE = r"[\w/'-]"
"""Characters that continue a word, so a phrase in a cell must not touch one at either end."""


class _QuestionFields(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: int
    question: str
    answer: str


class LookupQuestion(_QuestionFields):
    """The value of `target_column` in the row whose `key_column` holds `key_value`.

    `kind` is quote when the target column is a prose column, and lookup otherwise. `row_index` is the 0-based index of that data row. `column_distance` is the absolute difference between the positions of the key and target columns, 1 for adjacent columns. `key_near_duplicate` is true when another value in the key column is one character edit from `key_value`.
    """

    kind: Literal["lookup", "quote"] = "lookup"
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


class SearchQuestion(_QuestionFields):
    """The values of `target_column` in every row whose `search_column` cell contains `phrase`, in table order, joined by newlines.

    `target_column` is a key column. `phrase` is found in the same rows whether matched as a substring, as whole words, ignoring case, or with punctuation between its words, so the question has one reading. `row_indices` are the 0-based indices of the matching data rows.
    """

    kind: Literal["search"] = "search"
    search_column: str
    phrase: str
    target_column: str
    row_indices: tuple[int, ...]


type Question = Annotated[LookupQuestion | RowQuestion | FilterQuestion | SearchQuestion, Field(discriminator="kind")]


@dataclass(frozen=True)
class PhraseMatch:
    """A search phrase and the rows of the prose column at position `column` whose cells contain it."""

    column: int
    phrase: str
    row_indices: tuple[int, ...]


def make_questions(rng: Random, table: Table, kinds: Sequence[QuestionKind], count: int) -> tuple[Question, ...]:
    """`count` questions about `table`, cycling through `kinds`."""
    asked = list(islice(cycle(kinds), count))
    keys = _positions(table, "key")
    conditions = [
        (i, value)
        for i, column in enumerate(table)
        if column.role == "repeating"
        for value, matches in Counter(column.values).items()
        if matches in MATCHING_ROWS
    ]
    if "filter" in asked and not conditions:
        raise GenerationError(
            f"filter questions need a value that repeats in {MATCHING_ROWS.start} to {MATCHING_ROWS.stop - 1} rows of one column, and this table has none; change --rows or --columns, or drop filter from --kinds"
        )
    phrase_matches = find_phrase_matches(table) if "search" in asked else []
    if "search" in asked and not phrase_matches:
        raise GenerationError(
            f"search questions need a three-word phrase found in {MATCHING_ROWS.start} to {MATCHING_ROWS.stop - 1} prose cells of one column, and this table has none; raise --prose-columns or --rows, or drop search from --kinds"
        )
    if "quote" in asked and not _positions(table, "prose"):
        raise GenerationError("quote questions need a prose column; raise --prose-columns, or drop quote from --kinds")
    if "lookup" in asked and len(table) - len(_positions(table, "prose")) < 2:
        raise GenerationError(
            "lookup questions need two columns that are not prose; raise --columns or lower --prose-columns, or drop lookup from --kinds"
        )
    return tuple(
        make_question(rng, table, kind, question_id, keys, conditions, phrase_matches)
        for question_id, kind in enumerate(asked)
    )


def make_question(
    rng: Random,
    table: Table,
    kind: QuestionKind,
    question_id: int,
    keys: Sequence[int],
    conditions: Sequence[tuple[int, str]],
    phrase_matches: Sequence[PhraseMatch],
) -> Question:
    """`keys` are the positions of key columns; `conditions` are (column position, value) pairs allowed as filter conditions; `phrase_matches` are the phrase matches allowed in search questions."""
    match kind:
        case "lookup" | "quote":
            return lookup_question(rng, table, kind, question_id, keys)
        case "row":
            return row_question(rng, table, question_id, keys)
        case "filter":
            return filter_question(rng, table, question_id, conditions)
        case "search":
            return search_question(rng, table, question_id, keys, phrase_matches)


def lookup_question(
    rng: Random, table: Table, kind: Literal["lookup", "quote"], question_id: int, keys: Sequence[int]
) -> LookupQuestion:
    key, row_index = _key_and_row(rng, table, keys)
    target = _other_column(rng, table, key) if kind == "lookup" else pick(rng, _positions(table, "prose"))
    key_value = table[key].values[row_index]
    return LookupQuestion(
        kind=kind,
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


def search_question(
    rng: Random, table: Table, question_id: int, keys: Sequence[int], phrase_matches: Sequence[PhraseMatch]
) -> SearchQuestion:
    phrase_match = pick(rng, phrase_matches)
    target = pick(rng, keys)
    return SearchQuestion(
        question_id=question_id,
        question=f'List the value of column "{table[target].header}" in every row whose "{table[phrase_match.column].header}" cell contains the exact words "{phrase_match.phrase}", in table order, one value per line. Reply with those lines and nothing else.',
        answer="\n".join(table[target].values[i] for i in phrase_match.row_indices),
        search_column=table[phrase_match.column].header,
        phrase=phrase_match.phrase,
        target_column=table[target].header,
        row_indices=phrase_match.row_indices,
    )


def find_phrase_matches(table: Table) -> list[PhraseMatch]:
    """Phrases of three letter-only words, each found within one paragraph of `MATCHING_ROWS` cells of a prose column, in the same cells whether matched as a substring, as whole words, ignoring case, or with punctuation between its words."""
    return [
        phrase_match
        for column in _positions(table, "prose")
        for phrase_match in _column_phrase_matches(column, table[column].values)
    ]


def _column_phrase_matches(column: int, cells: Sequence[str]) -> Iterator[PhraseMatch]:
    loose = [SEPARATOR.sub(" ", cell.lower()) for cell in cells]
    for phrase in _repeated_phrases(cells):
        rows = tuple(i for i, cell in enumerate(cells) if phrase in cell)
        whole_words = rf"(?<!{WORD_EDGE}){re.escape(phrase)}(?!{WORD_EDGE})"
        if (
            len(rows) in MATCHING_ROWS
            and rows == tuple(i for i, cell in enumerate(loose) if phrase.lower() in cell)
            and all(re.search(whole_words, cells[i]) for i in rows)
        ):
            yield PhraseMatch(column, phrase, rows)


def _repeated_phrases(cells: Sequence[str]) -> list[str]:
    """Phrases that occur as three consecutive whitespace-separated words of one paragraph in `MATCHING_ROWS` cells, sorted."""
    counts = Counter(
        phrase
        for cell in cells
        for phrase in {
            " ".join(words[i : i + 3])
            for paragraph in cell.split(PARAGRAPH_BREAK)
            for words in [paragraph.split()]
            for i in range(len(words) - 2)
        }
        if PHRASE.fullmatch(phrase)
    )
    return sorted(phrase for phrase, count in counts.items() if count in MATCHING_ROWS)


def _key_and_row(rng: Random, table: Table, keys: Sequence[int]) -> tuple[int, int]:
    return pick(rng, keys), randbelow(rng, len(table[0].values))


def _other_column(rng: Random, table: Table, excluded: int) -> int:
    """A column other than `excluded` that is not prose."""
    return pick(rng, [i for i, column in enumerate(table) if i != excluded and column.role != "prose"])


def _positions(table: Table, role: ColumnRole) -> list[int]:
    return [i for i, column in enumerate(table) if column.role == role]


def _has_near_duplicate(values: Sequence[str], value: str) -> bool:
    return any(one_edit_apart(value, other) for other in values)
