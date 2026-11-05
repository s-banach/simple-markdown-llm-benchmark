from dataclasses import dataclass, replace
from itertools import islice
from random import Random

from simple_markdown_llm_benchmark.columns import LOWERCASE, ORDER_COLUMNS, ColumnSpec
from simple_markdown_llm_benchmark.config import BenchmarkConfig
from simple_markdown_llm_benchmark.sampling import GenerationError, distinct_draws, near_duplicate, shuffled, zipf_draws


@dataclass(frozen=True)
class Column:
    header: str
    values: tuple[str, ...]
    is_key: bool
    """Built to give every row a different value, so a value identifies one row. Other columns can be all distinct by chance, but nobody looks up a row by them."""


type Table = tuple[Column, ...]


def generate_table(rng: Random, config: BenchmarkConfig) -> Table:
    return tuple(
        Column(
            spec.header,
            tuple(column_values(rng, spec, config.rows, config.near_duplicates)),
            is_key=spec.distinct is None,
        )
        for spec in column_specs(rng, config)
    )


def column_specs(rng: Random, config: BenchmarkConfig) -> list[ColumnSpec]:
    """The first `config.columns` order-table columns, repeating them with suffixed headers when needed."""
    layout = [(ORDER_COLUMNS[i % len(ORDER_COLUMNS)], i // len(ORDER_COLUMNS)) for i in range(config.columns)]
    match config.content:
        case "plausible":
            return [replace(spec, header=f"{spec.header}_{repeat + 1}") if repeat else spec for spec, repeat in layout]
        case "gibberish":
            available = len(LOWERCASE) ** config.cell_length
            needed = max(config.columns, config.rows, *(spec.distinct or 0 for spec, _ in layout))
            if needed > available:
                raise GenerationError(
                    f"--cell-length {config.cell_length} allows {available} distinct strings, but this table needs {needed}; raise --cell-length"
                )
            space = (LOWERCASE,) * config.cell_length
            headers = list(distinct_draws(rng, space, config.columns))
            return [ColumnSpec(header, space, spec.distinct) for header, (spec, _) in zip(headers, layout)]


def column_values(rng: Random, spec: ColumnSpec, rows: int, near_duplicates: float) -> list[str]:
    try:
        if spec.distinct is None:
            return key_values(rng, spec, rows, near_duplicates)
        return zipf_draws(rng, list(distinct_draws(rng, spec.space, spec.distinct)), rows)
    except GenerationError as error:
        raise GenerationError(f"column {spec.header!r}: {error}") from error


def key_values(rng: Random, spec: ColumnSpec, rows: int, near_duplicates: float) -> list[str]:
    """`rows` distinct values, of which a `near_duplicates` fraction come in pairs one character edit apart."""
    pairs = round(near_duplicates * rows) // 2
    drawn = distinct_draws(rng, spec.space, rows - pairs)
    values = dict.fromkeys(drawn)
    for parts in islice(drawn.values(), pairs):
        values[near_duplicate(rng, spec.space, parts, values)] = None
    return shuffled(rng, list(values))


def render_markdown(table: Table, pad: bool) -> str:
    """Header line, separator line, then one line per data row."""
    widths = (
        tuple(max(3, len(column.header), *map(len, column.values)) for column in table) if pad else (0,) * len(table)
    )
    headers = tuple(column.header for column in table)
    separator = tuple("-" * max(3, width) for width in widths)
    data_rows = zip(*(column.values for column in table), strict=True)
    return "\n".join(
        "| " + " | ".join(cell.ljust(width) for cell, width in zip(row, widths)) + " |"
        for row in (headers, separator, *data_rows)
    )
