from dataclasses import dataclass, replace
from itertools import islice
from random import Random
from typing import Literal

from simple_markdown_llm_benchmark.columns import LOWERCASE, ORDER_COLUMNS, ColumnSpec
from simple_markdown_llm_benchmark.config import BenchmarkConfig
from simple_markdown_llm_benchmark.prose import PROSE_HEADER, prose_values
from simple_markdown_llm_benchmark.sampling import GenerationError, distinct_draws, near_duplicate, shuffled, zipf_draws

type ColumnRole = Literal["key", "repeating", "prose"]
"""
- key: built to give every row a different value, so a value identifies one row.
- repeating: drawn with replacement from a fixed set of values. A small table can get all different values by chance, but nobody looks up a row by them.
- prose: one passage per row, from the prose module.
"""


@dataclass(frozen=True)
class Column:
    header: str
    values: tuple[str, ...]
    role: ColumnRole


type Table = tuple[Column, ...]

type Row = tuple[str, ...]
"""The cells of one table line, from left to right."""


def generate_table(rng: Random, config: BenchmarkConfig) -> Table:
    """The order-table columns, then the prose columns."""
    specs, prose_headers = column_specs(rng, config)
    order_columns = tuple(
        Column(
            spec.header,
            tuple(column_values(rng, spec, config.rows, config.near_duplicates)),
            "key" if spec.distinct is None else "repeating",
        )
        for spec in specs
    )
    passages = prose_values(rng, config.content, config.prose_length, config.rows, len(prose_headers))
    return order_columns + tuple(
        Column(header, values, "prose") for header, values in zip(prose_headers, passages, strict=True)
    )


def column_specs(rng: Random, config: BenchmarkConfig) -> tuple[list[ColumnSpec], list[str]]:
    """Specs of the first `config.columns - config.prose_columns` order-table columns, repeating them with suffixed headers when needed, and the headers of the prose columns."""
    order_count = config.columns - config.prose_columns
    layout = [(ORDER_COLUMNS[i % len(ORDER_COLUMNS)], i // len(ORDER_COLUMNS)) for i in range(order_count)]
    match config.content:
        case "plausible":
            specs = [replace(spec, header=suffixed(spec.header, repeat)) for spec, repeat in layout]
            return specs, [suffixed(PROSE_HEADER, repeat) for repeat in range(config.prose_columns)]
        case "gibberish":
            available = len(LOWERCASE) ** config.cell_length
            needed = max(config.columns, config.rows, *(spec.distinct or 0 for spec, _ in layout))
            if needed > available:
                raise GenerationError(
                    f"--cell-length {config.cell_length} allows {available} distinct strings, but this table needs {needed}; raise --cell-length"
                )
            space = (LOWERCASE,) * config.cell_length
            headers = list(distinct_draws(rng, space, config.columns))
            specs = [
                ColumnSpec(header, space, spec.distinct)
                for header, (spec, _) in zip(headers[:order_count], layout, strict=True)
            ]
            return specs, headers[order_count:]


def suffixed(header: str, repeat: int) -> str:
    """`header` for the first use of a column, `header_2` for the second, and so on."""
    return f"{header}_{repeat + 1}" if repeat else header


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


def parse_markdown(markdown: str) -> tuple[Row, tuple[Row, ...]]:
    """Headers and data rows of a table from `render_markdown`, with padding stripped."""
    headers, _separator, *data_rows = (
        tuple(cell.strip() for cell in line.removeprefix("| ").removesuffix(" |").split(" | "))
        for line in markdown.split("\n")
    )
    return headers, tuple(data_rows)
