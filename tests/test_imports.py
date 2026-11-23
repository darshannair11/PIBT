"""The repo imports cleanly. These tests pass on the empty skeleton."""

import importlib
import zlib

import pytest

MODULES = [
    "mapf",
    "mapf.grid",
    "mapf.dist",
    "mapf.pibt",
    "mapf.validate",
    "mapf.metrics",
    "mapf.seeds",
    "experiments.crosscheck",
    "experiments.run_compare",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)


def test_derive_seed_is_crc32_of_joined_parts():
    from mapf.seeds import derive_seed

    assert derive_seed("empty-8-8", "random-1", 10, 0) == zlib.crc32(b"empty-8-8|random-1|10|0")
    assert derive_seed("a", 1) != derive_seed("a", 2)
    assert 0 <= derive_seed("anything") < 2**32
