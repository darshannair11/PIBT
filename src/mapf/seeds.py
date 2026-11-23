"""Deterministic seeds.

Not part of Algorithm 1. Python's built-in hash() is salted per process, so it
must never be used for seeds. Every seed in this project comes from here.
"""

from __future__ import annotations

import zlib


def derive_seed(*parts: object) -> int:
    """Return a 32-bit seed that depends only on the given parts.

    Not part of Algorithm 1; it feeds the random tie-break at Line 10 and the
    choice of epsilon_i at Line 2.

    Example:
        derive_seed("random-32-32-20", "random-1", 100, 3)
    gives the same integer on every machine and every run.
    """
    key = "|".join(str(p) for p in parts)
    return zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF
