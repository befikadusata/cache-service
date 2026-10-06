"""Replaceable string transformation and composition of completed results."""

from collections.abc import Sequence
from typing import Protocol


class Transformer(Protocol):
    """Async operation callers can replace with an external service or test double.

    Failures propagate to the application layer; only successful results may be cached.
    Replacement semantics must use a matching transformer version in input identities.
    """

    async def __call__(self, source: str) -> str: ...


async def uppercase_transform(source: str) -> str:
    """Apply Python's Unicode uppercase conversion for the uppercase-v1 behavior."""
    return source.upper()


def compose_output(list1: Sequence[str], list2: Sequence[str]) -> str:
    """Interleave already transformed values, preserving order and empty elements.

    Unequal lengths are an application error rather than a reason to truncate output.
    """
    return ", ".join(value for pair in zip(list1, list2, strict=True) for value in pair)
