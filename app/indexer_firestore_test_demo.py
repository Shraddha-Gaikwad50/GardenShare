"""Temporary demo module for GitHub webhook → code-indexer → Firestore tests.

Not imported by GardenShare. Safe to delete after indexing verification.
"""


class FirestoreIndexerDemo:
    """Temporary demo class for testing code indexing."""

    def build_index_record(self, repository: str, path: str) -> dict:
        return {
            "repository": repository,
            "path": path,
            "source": "firestore-indexer-demo",
        }

    def validate_index_record(self, record: dict) -> bool:
        return bool(record.get("repository") and record.get("path"))


def demo_index_message(repository: str) -> str:
    return f"Indexing repository: {repository}"
