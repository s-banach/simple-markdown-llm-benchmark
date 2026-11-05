"""Grade a model's answers to a test set by exact match, and classify each wrong answer by what went wrong."""

import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import CliApp, CliPositionalArg, SettingsConfigDict

from simple_markdown_llm_benchmark.benchmark import TableRecord
from simple_markdown_llm_benchmark.config import QuestionKind, setting_name
from simple_markdown_llm_benchmark.questions import (
    FilterQuestion,
    LookupQuestion,
    Question,
    RowQuestion,
    SearchQuestion,
)
from simple_markdown_llm_benchmark.sampling import one_edit_apart
from simple_markdown_llm_benchmark.table import Row, parse_markdown
from simple_markdown_llm_benchmark.testset import parse_answers, read_keys, read_replies

ErrorClass = Literal[
    "no answer",
    "wrong column",
    "wrong row",
    "near-duplicate row",
    "wrong row and column",
    "not in table",
    "partial",
    "breaks changed",
    "edited",
    "wrong cell count",
    "wrong cells",
    "rows missed",
    "rows added",
    "wrong order",
    "wrong values",
]
"""
- no answer: the reply has no block for the question, or an empty one.
- wrong column: a lookup or quote answer from another cell of the right row, or a filter or search answer holding the values of another column of the matching rows.
- wrong row, near-duplicate row: a lookup or quote answer from the target column of another row, or a row copy of another row; near-duplicate when that row's key is one character edit from the asked key.
- wrong row and column: a lookup or quote answer found in the table, but neither in the right row nor in the target column.
- not in table: a lookup answer found nowhere in the table.
- partial, breaks changed, edited: a quote answer found nowhere in the table. Partial when its text, ignoring <br> tags, line breaks and spaces, is part of the passage, such as its first paragraph; breaks changed when it has all the passage's words but other <br> tags, line breaks or spaces between them; edited otherwise.
- wrong cell count, wrong cells: a row copy with too few or too many cells, or with some cells wrong.
- rows missed, rows added, wrong order: a filter or search answer that lacks some right values, has extra values, or has the right values in another order.
- wrong values: a filter or search answer with both missing and extra values.
"""

BREAK_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)


class QuestionResult(BaseModel):
    """`error` is None when `given` equals the answer."""

    model_config = ConfigDict(frozen=True)

    test: str
    setting: str
    question: Question
    given: str | None
    error: ErrorClass | None


class GradeOptions(BaseModel):
    """Grade answers to a test set by exact match. Prints accuracy by setting and question kind, counts wrong answers by class, and prints the share of right values found in filter and search answers."""

    model_config = SettingsConfigDict(
        frozen=True, cli_kebab_case=True, cli_prog_name="simple-markdown-llm-benchmark-grade"
    )

    testset: CliPositionalArg[Path] = Field(description="Test set directory, holding keys/<test>.json.")
    answers: CliPositionalArg[Path] = Field(
        description="Directory holding the model's reply to tests/<test>.txt as <test>.txt. A missing reply counts as no answer."
    )
    details: Path | None = Field(
        None, description="Write one JSON line per question, with the answer given and its error class, to this file."
    )


def grade_record(test: str, record: TableRecord, answers: Mapping[int, str]) -> list[QuestionResult]:
    """`answers` holds the given answers keyed by `question_id`."""
    headers, rows = parse_markdown(record.markdown)
    return [
        QuestionResult(
            test=test,
            setting=setting_name(record.config),
            question=question,
            given=(given := answers.get(question.question_id)),
            error=classify(question, given, headers, rows),
        )
        for question in record.questions
    ]


def classify(question: Question, given: str | None, headers: Row, rows: Sequence[Row]) -> ErrorClass | None:
    if not given:
        return "no answer"
    if given == question.answer:
        return None
    match question:
        case LookupQuestion():
            return classify_lookup(question, given, headers, rows)
        case RowQuestion():
            return classify_row(question, given, headers, rows)
        case FilterQuestion() | SearchQuestion():
            return classify_list(question, given, headers, rows)


def classify_lookup(question: LookupQuestion, given: str, headers: Row, rows: Sequence[Row]) -> ErrorClass:
    if given in rows[question.row_index]:
        return "wrong column"
    target = headers.index(question.target_column)
    return other_row(question, [row for row in rows if row[target] == given], headers) or (
        "wrong row and column" if any(given in row for row in rows) else not_in_table(question, given)
    )


def not_in_table(question: LookupQuestion, given: str) -> ErrorClass:
    """The class of a lookup or quote answer found nowhere in the table."""
    if question.kind == "lookup":
        return "not in table"
    given_words, answer_words = words(given), words(question.answer)
    if given_words == answer_words:
        return "breaks changed"
    if given_words and " ".join(given_words) in " ".join(answer_words):
        return "partial"
    return "edited"


def words(text: str) -> list[str]:
    """`text` split at whitespace and <br> tags."""
    return BREAK_TAG.sub(" ", text).split()


def classify_row(question: RowQuestion, given: str, headers: Row, rows: Sequence[Row]) -> ErrorClass:
    cells = tuple(given.split("\n"))
    if len(cells) != len(headers):
        return "wrong cell count"
    return other_row(question, [row for row in rows if row == cells], headers) or "wrong cells"


def other_row(question: LookupQuestion | RowQuestion, sources: Sequence[Row], headers: Row) -> ErrorClass | None:
    """The class of an answer taken from one of `sources`, rows other than the asked one; None when `sources` is empty."""
    if not sources:
        return None
    key = headers.index(question.key_column)
    return "near-duplicate row" if any(one_edit_apart(row[key], question.key_value) for row in sources) else "wrong row"


def classify_list(
    question: FilterQuestion | SearchQuestion, given: str, headers: Row, rows: Sequence[Row]
) -> ErrorClass:
    expected = Counter(question.answer.split("\n"))
    lines = Counter(given.split("\n"))
    if lines == expected:
        return "wrong order"
    target = headers.index(question.target_column)
    if any(lines == Counter(rows[i][j] for i in question.row_indices) for j in range(len(headers)) if j != target):
        return "wrong column"
    missed, extra = expected - lines, lines - expected
    if not extra:
        return "rows missed"
    if not missed:
        return "rows added"
    return "wrong values"


def values_found(results: Sequence[QuestionResult]) -> str:
    """For each kind of question with a list answer, the share of the right values that the given answers hold, over all its questions."""
    found: Counter[QuestionKind] = Counter()
    expected: Counter[QuestionKind] = Counter()
    for result in results:
        if isinstance(result.question, FilterQuestion | SearchQuestion):
            right = Counter(result.question.answer.split("\n"))
            found[result.question.kind] += (right & Counter((result.given or "").split("\n"))).total()
            expected[result.question.kind] += right.total()
    return ", ".join(
        f"{kind} {found[kind]}/{expected[kind]} ({found[kind] / expected[kind]:.1%})"
        for kind in get_args(QuestionKind)
        if expected[kind]
    )


def report(results: Sequence[QuestionResult]) -> str:
    """Accuracy by setting and question kind, wrong answers counted by class, and the share of right values found in list answers."""
    kinds = [kind for kind in get_args(QuestionKind) if any(result.question.kind == kind for result in results)]
    settings = list(dict.fromkeys(result.setting for result in results))
    width = max(map(len, [*settings, "setting"]))

    def line(label: str, group: Sequence[QuestionResult]) -> str:
        groups = [*([result for result in group if result.question.kind == kind] for kind in kinds), group]
        rights = [sum(result.error is None for result in g) for g in groups]
        return (
            f"{label:{width}}"
            + "".join(f"{f'{right}/{len(g)}':>10}" for right, g in zip(rights, groups))
            + f"  {rights[-1] / len(group):6.1%}"
        )

    header = f"{'setting':{width}}" + "".join(f"{kind:>10}" for kind in [*kinds, "all"])
    rows = [line(setting, [result for result in results if result.setting == setting]) for setting in settings]
    errors = Counter(result.error for result in results if result.error is not None)
    error_line = ", ".join(f"{error} {count}" for error, count in errors.most_common()) or "none"
    lines = [header, *rows, line("all", results), "", f"wrong answers by class: {error_line}"]
    found = values_found(results)
    return "\n".join([*lines, f"right values found in list answers: {found}"] if found else lines)


def main() -> None:
    try:
        options = CliApp.run(GradeOptions)
        keys = read_keys(options.testset)
        replies = read_replies(options.answers, keys)
    except (ValueError, OSError) as error:
        sys.exit(f"error: {error}")
    results = [
        result
        for test, record in keys.items()
        for result in grade_record(test, record, parse_answers(replies.get(test, "")))
    ]
    missing = [test for test in keys if test not in replies]
    if missing:
        print(
            f"no reply for {len(missing)} of {len(keys)} tests, graded as no answer: {', '.join(missing)}",
            file=sys.stderr,
        )
    print(report(results))
    if options.details is not None:
        try:
            options.details.write_text("".join(result.model_dump_json() + "\n" for result in results), encoding="utf-8")
        except OSError as error:
            sys.exit(f"error: {error}")


if __name__ == "__main__":
    main()
