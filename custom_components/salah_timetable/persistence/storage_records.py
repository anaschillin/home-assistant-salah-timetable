"""Immutable persisted snapshot, staged import and approval model types."""

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from types import MappingProxyType
from typing import Any, Mapping

from ..domain.model import Timetable
from ..parsers.import_model import ImportCandidate
from ..sources.source_model import RemoteSource


class PendingImportError(ValueError):
    """A proposal must be reviewed before another can be staged."""


class RamadanApprovalError(ValueError):
    """A proposal cannot safely resolve under the current Ramadan settings."""


class ReviewChangedError(ValueError):
    """The approved source changed after the replacement comparison was shown."""


@dataclass(frozen=True)
class ImportReviewBaseline:
    """Exact approved records and provenance used by a replacement review."""

    timetable: Timetable | None
    source: ImportCandidate | None


@dataclass(frozen=True)
class StagedImport:
    """A durable proposal; its identity prevents stale previews being approved."""

    stage_id: str
    candidate: ImportCandidate

    def as_dict(self) -> dict:
        return {"stage_id": self.stage_id, "candidate": self.candidate.as_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "StagedImport":
        stage_id = data["stage_id"]
        if (
            not isinstance(stage_id, str)
            or len(stage_id) != 32
            or any(char not in "0123456789abcdef" for char in stage_id)
        ):
            raise ValueError("Invalid staged import identity")
        return cls(stage_id, ImportCandidate.from_dict(data["candidate"]))


@dataclass(frozen=True)
class _Snapshot:
    timetables: tuple[Timetable, ...]
    approved_sources: Mapping[str, ImportCandidate]
    staged: StagedImport | None
    remote_sources: Mapping[str, RemoteSource] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )
    remote_checks: Mapping[str, Mapping[str, Any]] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )

    def as_dict(self) -> dict:
        return {
            "timetables": [table.as_dict() for table in self.timetables],
            "approved_sources": {
                key: candidate.as_dict()
                for key, candidate in self.approved_sources.items()
            },
            "staged": self.staged.as_dict() if self.staged else None,
            "remote_sources": {
                key: source.as_dict() for key, source in self.remote_sources.items()
            },
            "remote_checks": {
                key: dict(check) for key, check in self.remote_checks.items()
            },
        }


