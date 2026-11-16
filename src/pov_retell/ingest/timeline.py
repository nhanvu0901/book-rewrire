"""What one character knows at a point in the story, read from a run's JSON files (T-0017)."""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

POINT = re.compile(r"u(\d+)(?:_s(\d+))?")
WHOLE_CHAPTER = 10**9
TRUTH_FROM_STANCE = {"believes": "true", "disbelieves": "false"}


@dataclass(frozen=True)
class Learned:
    acquisition_id: str
    segment_id: str
    channel: str
    stance: str
    source_id: str | None


@dataclass(frozen=True)
class KnownClaim:
    claim_id: str
    statement: str
    stance: str
    known_truth: str | None
    history: list[Learned]
    truth: str | None = None  # the book's truth; only filled with reveal=True


@dataclass(frozen=True)
class CharacterKnowledge:
    run_id: str
    character_id: str
    name: str
    until: str | None
    claims: list[KnownClaim] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def point(text: str) -> tuple[int, int]:
    """`u05` -> (5, whole chapter); `u05_s2` -> (5, 2)."""
    match = POINT.fullmatch(text)
    if match is None:
        raise ValueError(f"expected a chapter (u05) or scene (u05_s2) ID, got {text!r}")
    return int(match.group(1)), int(match.group(2)) if match.group(2) else WHOLE_CHAPTER


def _acquisition_order(record: dict[str, Any]) -> tuple[int, int, int]:
    if record["channel"] == "prior":
        return (0, 0, 0)  # known before the story began
    chapter, segment = point(record["segment_id"])
    return (chapter, segment, int(record["acquisition_id"].rsplit("_k", 1)[1]))


def latest_run(ingest_dir: Path, book_id: str) -> Path:
    runs = [p for p in (ingest_dir / book_id).glob("run_*") if (p / "knowledge.json").exists()]
    if not runs:
        raise ValueError(f"no run with knowledge.json for {book_id!r} under {ingest_dir}")
    return max(runs, key=lambda p: p.stat().st_mtime)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_character(run_dir: Path, query: str) -> dict[str, Any]:
    characters: list[dict[str, Any]] = _read(run_dir / "characters.json")
    redirects: dict[str, str] = _read(run_dir / "identity_redirects.json")
    wanted = redirects.get(query, query)
    by_id = [c for c in characters if c["character_id"] == wanted]
    if by_id:
        return by_id[0]
    key = query.casefold()
    by_name = [
        c
        for c in characters
        if key in {n.casefold() for n in [c["candidate_name"], *c.get("aliases", [])]}
    ]
    if len(by_name) == 1:
        return by_name[0]
    if by_name:
        ids = ", ".join(c["character_id"] for c in by_name)
        raise ValueError(f"{query!r} matches several characters ({ids}); use an ID")
    raise ValueError(f"no character {query!r} in {run_dir.name}")


def knowledge_at(
    run_dir: Path, character: str, until: str | None = None, *, reveal: bool = False
) -> CharacterKnowledge:
    """Claims the character holds at `until` (inclusive; the whole story when None)."""
    person = find_character(run_dir, character)
    limit = point(until) if until is not None else (WHOLE_CHAPTER, WHOLE_CHAPTER)
    claims = {c["claim_id"]: c for c in _read(run_dir / "claims.json")}
    records = sorted(
        (
            k
            for k in _read(run_dir / "knowledge.json")
            if k["character_id"] == person["character_id"]
            and (k["channel"] == "prior" or point(k["segment_id"]) <= limit)
        ),
        key=_acquisition_order,
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["claim_id"], []).append(record)

    known: list[KnownClaim] = []
    for claim_id, history in grouped.items():
        learned = [k for k in history if k["channel"] == "learns_truth"]
        known.append(
            KnownClaim(
                claim_id=claim_id,
                statement=claims[claim_id]["statement"],
                stance=history[-1]["stance"],
                known_truth=TRUTH_FROM_STANCE.get(learned[-1]["stance"]) if learned else None,
                history=[
                    Learned(
                        acquisition_id=k["acquisition_id"],
                        segment_id=k["segment_id"],
                        channel=k["channel"],
                        stance=k["stance"],
                        source_id=k["source_id"],
                    )
                    for k in history
                ],
                truth=claims[claim_id]["truth"] if reveal else None,
            )
        )
    return CharacterKnowledge(
        run_id=run_dir.name,
        character_id=person["character_id"],
        name=person["candidate_name"],
        until=until,
        claims=known,
    )


def format_knowledge(view: CharacterKnowledge) -> str:
    where = f"up to {view.until}" if view.until else "by the end of the run"
    lines = [f"{view.name} ({view.character_id}) {where}, {view.run_id}: {len(view.claims)} claims"]
    for claim in view.claims:
        knows = f"knows it is {claim.known_truth}" if claim.known_truth else "truth not known"
        lines.append(f"\n{claim.claim_id}  {claim.stance:<11}  {claim.statement}")
        lines.append(f"    {knows}" + (f" | book: {claim.truth}" if claim.truth else ""))
        for step in claim.history:
            via = f" via {step.source_id}" if step.source_id else ""
            lines.append(f"    - {step.segment_id} {step.channel} -> {step.stance}{via}")
    return "\n".join(lines)
