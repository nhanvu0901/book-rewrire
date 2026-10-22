from dataclasses import dataclass


@dataclass(frozen=True)
class Chapter:
    unit_id: str
    text: str
    paragraphs: dict[str, str]
