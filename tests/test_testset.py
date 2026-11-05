import hashlib
import json
from pathlib import Path

import pytest

from simple_markdown_llm_benchmark import (
    BenchmarkConfig,
    FilterQuestion,
    LookupQuestion,
    RowQuestion,
    generate,
    make_record,
)
from simple_markdown_llm_benchmark.benchmark_v1 import BenchmarkV1Options, settings
from simple_markdown_llm_benchmark.grade import grade_record, values_found
from simple_markdown_llm_benchmark.preset import records_by_setting
from simple_markdown_llm_benchmark.prose import PARAGRAPH_BREAK
from simple_markdown_llm_benchmark.sampling import one_edit_apart
from simple_markdown_llm_benchmark.table import parse_markdown
from simple_markdown_llm_benchmark.testset import (
    parse_answers,
    read_replies,
    records_by_test,
    render_testset,
    write_testset,
)

RECORD = make_record(BenchmarkConfig(rows=40, columns=12, near_duplicates=1, questions=12), 0)


def test_exact_answers_pass_despite_harness_formatting(tmp_path: Path) -> None:
    """Line endings, indentation, blank lines and a byte order mark, as harnesses and editors add them."""
    reply = "".join(
        f"  === Q{question.question_id + 1} \r\n\r\n"
        + "".join(f"  {line} \r\n" for line in question.answer.split("\n"))
        for question in RECORD.questions
    )
    (tmp_path / "t.txt").write_text(reply, encoding="utf-8-sig")
    answers = parse_answers(read_replies(tmp_path, ["t"])["t"])
    assert [result.error for result in grade_record("t", RECORD, answers)] == [None] * len(RECORD.questions)


def test_wrong_answers_are_classified() -> None:
    headers, rows = parse_markdown(RECORD.markdown)
    lookups = [question for question in RECORD.questions if isinstance(question, LookupQuestion)]
    row = next(question for question in RECORD.questions if isinstance(question, RowQuestion))
    missed, *others = [question for question in RECORD.questions if isinstance(question, FilterQuestion)]
    repeated = next(
        question for question in others if question.answer.split("\n")[0] != question.answer.split("\n")[-1]
    )
    key = headers.index(row.key_column)
    near_duplicate = next(cells for cells in rows if one_edit_apart(cells[key], row.key_value))
    other_key = rows[(lookups[2].row_index + 1) % len(rows)][headers.index(lookups[2].key_column)]
    repeated_lines = repeated.answer.split("\n")
    given = {
        lookups[0].question_id: (lookups[0].key_value, "wrong column"),
        lookups[1].question_id: ("not a cell", "not in table"),
        lookups[2].question_id: (other_key, "wrong row and column"),
        lookups[3].question_id: ("", "no answer"),
        row.question_id: ("\n".join(near_duplicate), "near-duplicate row"),
        missed.question_id: (missed.answer.rsplit("\n", 1)[0], "rows missed"),
        repeated.question_id: ("\n".join([*repeated_lines[:-1], repeated_lines[0]]), "wrong values"),
    }
    reply = "".join(f"=== Q{question_id + 1}\n{answer}\n" for question_id, (answer, _) in given.items())
    errors = {result.question.question_id: result.error for result in grade_record("t", RECORD, parse_answers(reply))}
    assert errors == {question.question_id: "no answer" for question in RECORD.questions} | {
        question_id: error for question_id, (_, error) in given.items()
    }


def test_wrong_quotes_are_classified() -> None:
    config = BenchmarkConfig(rows=20, columns=4, prose_columns=1, questions=6, kinds=("quote",))
    record = make_record(config, 0)
    right, partial, cut_off, breaks, edited, only_breaks = record.questions
    given = {
        right.question_id: (right.answer, None),
        partial.question_id: (partial.answer.split(PARAGRAPH_BREAK)[0], "partial"),
        cut_off.question_id: ("\n".join(cut_off.answer.split(PARAGRAPH_BREAK)[:-1]), "partial"),
        breaks.question_id: (breaks.answer.replace(PARAGRAPH_BREAK, "\n"), "breaks changed"),
        edited.question_id: (edited.answer + " Thank you.", "edited"),
        only_breaks.question_id: (PARAGRAPH_BREAK, "edited"),
    }
    reply = "".join(f"=== Q{question_id + 1}\n{answer}\n" for question_id, (answer, _) in given.items())
    errors = {result.question.question_id: result.error for result in grade_record("t", record, parse_answers(reply))}
    assert errors == {question_id: error for question_id, (_, error) in given.items()}


def test_search_answers_count_the_right_values_found() -> None:
    record = make_record(BenchmarkConfig(rows=100, columns=8, prose_columns=1, questions=2, kinds=("search",)), 0)
    right, missed = record.questions
    reply = f"=== Q1\n{right.answer}\n=== Q2\n{missed.answer.rsplit('\n', 1)[0]}\n"
    results = grade_record("t", record, parse_answers(reply))
    assert [result.error for result in results] == [None, "rows missed"]
    total = len(right.answer.split("\n")) + len(missed.answer.split("\n"))
    assert values_found(results) == f"search {total - 1}/{total} ({(total - 1) / total:.1%})"


def test_tests_are_named_by_setting_and_table() -> None:
    config = BenchmarkConfig(rows=5, columns=4, prose_columns=1, questions=2, kinds=("quote",), tables=2)
    records = list(generate(config))
    assert list(records_by_test(records)) == ["5x4_prose1_0", "5x4_prose1_1"]
    with pytest.raises(ValueError):
        records_by_test([*records, records[0]])


def test_paths_that_would_mix_or_lose_results_raise(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("")
    with pytest.raises(FileExistsError):
        write_testset(tmp_path / "file", {})
    with pytest.raises(NotADirectoryError):
        read_replies(tmp_path / "absent", [])


def test_benchmark_v1_seed_0_is_unchanged() -> None:
    """Pins the reference test set. If this fails, the change alters benchmark v1: release the new output as a new version instead."""
    options = BenchmarkV1Options(seed=0, tables=3)
    files = render_testset(records_by_setting(settings(options), options.tables))
    assert len(files) == 2 * 3 * len(settings(options))
    assert (
        hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        == "255f0832534ee26a33172052a12f047dbade060f273d8ded5256c190abf25781"
    )


def test_more_tables_extend_the_test_set() -> None:
    configs = settings(BenchmarkV1Options(seed=5))
    one, two = records_by_setting(configs, 1), records_by_setting(configs, 2)
    assert len(two) == 2 * len(configs)
    assert one.items() <= two.items()
