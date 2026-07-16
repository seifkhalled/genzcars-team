import itertools
import logging
from typing import TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


class KeyRotator(Generic[T]):
    """Thread-safe round-robin distributor over a pool of items.

    Used to rotate across ChatGroq instances (one per API key) so that
    successive LLM calls hit different keys, avoiding 429 rate limits.
    """

    def __init__(self, items: list[T]):
        if not items:
            raise ValueError("KeyRotator requires at least one item")
        self._items = items
        self._cycle = itertools.cycle(range(len(items)))
        self._count = 0

    def next(self) -> T:
        """Return the next item in round-robin order."""
        idx = next(self._cycle)
        self._count += 1
        return self._items[idx]

    @property
    def size(self) -> int:
        return len(self._items)

    @property
    def total_rotations(self) -> int:
        return self._count
