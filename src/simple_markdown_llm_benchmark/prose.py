"""Prose columns, which hold one passage per row: two or more paragraphs joined by PARAGRAPH_BREAK.

Passages are consumer complaint narratives received in July 2026, from the CFPB narratives archive (https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/). The archive flattens each narrative to one line, so each paragraph break replaces one space between sentences of the original text.

- `narratives_long.jsonl` holds 500 narratives of 530 to 1522 characters, counting each PARAGRAPH_BREAK.
- `narratives_short.jsonl` holds 466 of them shortened to at most 400 characters by deleting whole sentences, chosen by reading so each still tells its complaint. Kept sentences keep their order, and a paragraph break joins two kept sentences that the long text separates by one.
"""

import datetime
from functools import cache
from importlib.resources import files
from itertools import batched
from random import Random

from pydantic import BaseModel, ConfigDict

from simple_markdown_llm_benchmark.config import ProseLength
from simple_markdown_llm_benchmark.sampling import GenerationError, sample

PARAGRAPH_BREAK = "<br><br>"
PROSE_HEADER = "complaint"


class Narrative(BaseModel):
    """A CFPB complaint narrative as a passage. `complaint_id` and `date_received` identify it in the CFPB archive."""

    model_config = ConfigDict(frozen=True)

    complaint_id: int
    date_received: datetime.date
    text: str


@cache
def narratives(length: ProseLength) -> tuple[Narrative, ...]:
    lines = (
        files("simple_markdown_llm_benchmark")
        .joinpath(f"narratives_{length}.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    return tuple(Narrative.model_validate_json(line) for line in lines)


def prose_values(rng: Random, length: ProseLength, rows: int, columns: int) -> list[tuple[str, ...]]:
    """The passages of `columns` prose columns, `rows` per column, all different narratives."""
    pool = narratives(length)
    count = rows * columns
    if count > len(pool):
        raise GenerationError(
            f"{count} prose cells need different narratives, but only {len(pool)} exist; lower --rows or --prose-columns"
        )
    return list(batched((narrative.text for narrative in sample(rng, pool, count)), rows))
