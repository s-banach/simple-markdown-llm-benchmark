"""Random draws built only on `Random.random()`.

Python keeps the sequence from `Random.random()` stable across versions, but `choice`, `sample` and `shuffle` may change, so equal seeds give equal tables only if every draw goes through this module.
"""

import math
from bisect import bisect_left
from collections.abc import Collection, Sequence
from itertools import accumulate
from random import Random

type Space = tuple[tuple[str, ...], ...]
"""The strings formed by concatenating one entry from each part, in order."""

type Parts = tuple[str, ...]
"""One entry from each part of a space."""


class GenerationError(Exception):
    """The requested configuration cannot produce a valid table or question set."""


def randbelow(rng: Random, n: int) -> int:
    """Uniform integer in [0, n), exact for n below 2**53."""
    return int(rng.random() * n)


def pick[T](rng: Random, items: Sequence[T]) -> T:
    return items[randbelow(rng, len(items))]


def shuffled[T](rng: Random, items: Sequence[T]) -> list[T]:
    """Fisher-Yates shuffle into a new list."""
    result = list(items)
    for i in reversed(range(1, len(result))):
        j = randbelow(rng, i + 1)
        result[i], result[j] = result[j], result[i]
    return result


def distinct_draws(rng: Random, space: Space, count: int) -> dict[str, Parts]:
    """`count` draws from `space` with different joined strings, keyed by joined string, in random order.

    Raises GenerationError when `space` holds fewer than `count` strings.
    """
    size = math.prod(map(len, space))
    if count > size:
        raise GenerationError(f"needs {count} distinct values, but the value space holds only {size}")
    drawn: dict[str, Parts] = {}
    while len(drawn) < count:
        parts = tuple(pick(rng, part) for part in space)
        drawn.setdefault("".join(parts), parts)
    return drawn


def zipf_draws(rng: Random, vocabulary: Sequence[str], count: int) -> list[str]:
    """`count` draws with replacement, where the entry at rank r has weight 1/r.

    The skew gives every column both common and rare values, as real categorical columns have.
    """
    cumulative = list(accumulate(1 / rank for rank in range(1, len(vocabulary) + 1)))
    return [vocabulary[bisect_left(cumulative, rng.random() * cumulative[-1])] for _ in range(count)]


def near_duplicate(rng: Random, space: Space, parts: Parts, taken: Collection[str]) -> str:
    """A string of `space`, not in `taken`, one character edit from `"".join(parts)`.

    Edits touch only parts whose entries are single characters, such as the digits of an ID or a middle initial, so the result keeps the format of its column. A swap of two adjacent characters is chosen half the time when one is available, otherwise a substitution.
    """
    editable = [i for i, part in enumerate(space) if len(part) > 1 and all(len(entry) == 1 for entry in part)]
    swaps = [
        "".join((*parts[:i], parts[i + 1], parts[i], *parts[i + 2 :]))
        for i in editable
        if i + 1 in editable and space[i] == space[i + 1] and parts[i] != parts[i + 1]
    ]
    substitutions = [
        "".join((*parts[:i], entry, *parts[i + 1 :])) for i in editable for entry in space[i] if entry != parts[i]
    ]
    free_swaps = [value for value in swaps if value not in taken]
    free_substitutions = [value for value in substitutions if value not in taken]
    if not free_swaps and not free_substitutions:
        raise GenerationError(
            f"no unused value is one character edit from {''.join(parts)!r}; lower --near-duplicates or --rows"
        )
    if free_swaps and (not free_substitutions or rng.random() < 0.5):
        return pick(rng, free_swaps)
    return pick(rng, free_substitutions)


def one_edit_apart(a: str, b: str) -> bool:
    """True when `b` differs from `a` by one substituted character or one swap of adjacent characters."""
    if len(a) != len(b):
        return False
    differences = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    match differences:
        case [_]:
            return True
        case [i, j]:
            return j == i + 1 and a[i] == b[j] and a[j] == b[i]
        case _:
            return False
