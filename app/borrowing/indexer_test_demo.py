"""Temporary module used only for incremental indexing delete tests.

Safe to remove; it is not imported by the GardenShare application.
"""


def indexer_demo_marker() -> str:
    """Return a unique string for semantic retrieval smoke tests."""

    return "GardenShare indexer deletion demo marker"


def describe_demo_purpose() -> str:
    """Explain why this file exists in the repository briefly."""

    return "Validates that deleted source files are removed from the code index."
