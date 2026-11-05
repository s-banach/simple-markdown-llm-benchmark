"""Prose columns, which hold one passage per row: two or more paragraphs joined by PARAGRAPH_BREAK.

Plausible passages are the consumer complaint narratives in `narratives.jsonl`: 500 complaints received in July 2026, from the CFPB narratives archive (https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/). The archive flattens each narrative to one line, so each paragraph break replaces one space between sentences of the original text. Gibberish passages copy the paragraph word counts of a random narrative and fill them with random words.
"""

import datetime
from functools import cache
from importlib.resources import files
from itertools import batched
from random import Random

from pydantic import BaseModel, ConfigDict

from simple_markdown_llm_benchmark.columns import WORDS
from simple_markdown_llm_benchmark.config import Content
from simple_markdown_llm_benchmark.sampling import GenerationError, pick, sample

PARAGRAPH_BREAK = "<br><br>"
PROSE_HEADER = "complaint"
SENTENCE_WORDS = range(5, 16)
"""Allowed numbers of words in a gibberish sentence, except the last sentence of a paragraph, which takes the words left over."""


class Narrative(BaseModel):
    """A CFPB complaint narrative as a passage. `complaint_id` and `date_received` identify it in the CFPB archive."""

    model_config = ConfigDict(frozen=True)

    complaint_id: int
    date_received: datetime.date
    text: str


@cache
def narratives() -> tuple[Narrative, ...]:
    lines = files("simple_markdown_llm_benchmark").joinpath("narratives.jsonl").read_text().splitlines()
    return tuple(Narrative.model_validate_json(line) for line in lines)


def prose_values(rng: Random, content: Content, rows: int, columns: int) -> list[tuple[str, ...]]:
    """The passages of `columns` prose columns, `rows` per column. Plausible passages are all different narratives."""
    pool = narratives()
    count = rows * columns
    match content:
        case "plausible":
            if count > len(pool):
                raise GenerationError(
                    f"{count} prose cells need different narratives, but only {len(pool)} exist; lower --rows or --prose-columns"
                )
            passages = [narrative.text for narrative in sample(rng, pool, count)]
        case "gibberish":
            passages = [gibberish_passage(rng, pick(rng, pool).text) for _ in range(count)]
    return list(batched(passages, rows))


def gibberish_passage(rng: Random, shape: str) -> str:
    """Random words, with as many paragraphs and words per paragraph as the passage `shape`."""
    return PARAGRAPH_BREAK.join(
        gibberish_paragraph(rng, len(paragraph.split())) for paragraph in shape.split(PARAGRAPH_BREAK)
    )


def gibberish_paragraph(rng: Random, word_count: int) -> str:
    """`word_count` random words in sentences, each capitalized and ending with a period."""
    sentences: list[str] = []
    while word_count > 0:
        length = min(word_count, pick(rng, SENTENCE_WORDS))
        text = " ".join(pick(rng, WORDS) for _ in range(length))
        sentences.append(text.capitalize() + ".")
        word_count -= length
    return " ".join(sentences)
