"""An in-memory `GraphWriter`: lets the ingest graph run with no Neo4j.

It copies the one property of the real writer that the graph relies on: MERGE. Rows are keyed by
(book_id, id) and edges live in sets, so writing the same thing twice changes nothing.
"""

from typing import Any

Pairs = list[tuple[str, str]]


class FakeWriter:
    def __init__(self, fail_once_in: str | None = None) -> None:
        self.books: dict[str, dict[str, Any]] = {}
        self.units: dict[tuple[str, str], dict[str, Any]] = {}
        self.paragraphs: dict[tuple[str, str], dict[str, Any]] = {}
        self.unit_next: set[tuple[str, str, str]] = set()
        self.contains: set[tuple[str, str, str]] = set()
        self.paragraph_next: set[tuple[str, str, str]] = set()
        self.calls: list[str] = []
        self._fail_once_in = fail_once_in  # name of a method that raises on its first call

    def _call(self, name: str) -> None:
        self.calls.append(name)
        if self._fail_once_in == name:
            self._fail_once_in = None
            raise OSError(f"simulated crash in {name}")

    def ensure_schema(self) -> None:
        self._call("ensure_schema")

    def book_sha256(self, book_id: str) -> str | None:
        book = self.books.get(book_id)
        return book["sha256"] if book else None

    def delete_book(self, book_id: str) -> None:
        self._call("delete_book")
        for table in (self.units, self.paragraphs):
            for key in [k for k in table if k[0] == book_id]:
                del table[key]
        for edges in (self.unit_next, self.contains, self.paragraph_next):
            edges -= {e for e in edges if e[0] == book_id}

    def write_book(self, book: dict[str, Any]) -> None:
        self._call("write_book")
        self.books[book["id"]] = {**self.books.get(book["id"], {}), **book}

    def write_units(
        self, book_id: str, units: list[dict[str, Any]], next_pairs: Pairs, contains_pairs: Pairs
    ) -> None:
        self._call("write_units")
        for u in units:
            self.units[(book_id, u["id"])] = dict(u)
        self.unit_next |= {(book_id, a, b) for a, b in next_pairs}
        self.contains |= {(book_id, a, b) for a, b in contains_pairs}

    def write_paragraphs(
        self, book_id: str, paragraphs: list[dict[str, Any]], next_pairs: Pairs
    ) -> None:
        self._call("write_paragraphs")
        for p in paragraphs:
            self.paragraphs[(book_id, p["id"])] = dict(p)
        self.paragraph_next |= {(book_id, a, b) for a, b in next_pairs}

    def counts(self, book_id: str) -> dict[str, int]:
        units = sum(1 for k in self.units if k[0] == book_id)
        paragraphs = sum(1 for k in self.paragraphs if k[0] == book_id)
        return {
            "units": units,
            "paragraphs": paragraphs,
            "has_unit": units,  # the real writer MERGEs HAS_UNIT together with each unit
            "has_paragraph": paragraphs,
            "unit_next": sum(1 for e in self.unit_next if e[0] == book_id),
            "contains": sum(1 for e in self.contains if e[0] == book_id),
            "paragraph_next": sum(1 for e in self.paragraph_next if e[0] == book_id),
        }
