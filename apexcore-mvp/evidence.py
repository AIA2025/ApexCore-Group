"""Evidence-item model and reference formatting.

Every factual claim in the dossier (Ebene A) must carry an inline pointer to
the concrete piece of evidence it rests on: which file, which hash, which
page in the annex. This module is the single place that formats that
pointer, so the same "Anlage N / Datei / Hash / Seite" string looks
identical wherever it appears (Ebene A bullets, Ebene B table, Anlagenverzeichnis).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvidenceItem:
    anlage_nr: int
    filename: str
    description: str
    file_path: Path | None = None
    page_ref: str = ""
    sha256: str = ""

    def __post_init__(self):
        if self.file_path is not None and Path(self.file_path).exists() and not self.sha256:
            self.sha256 = hashlib.sha256(Path(self.file_path).read_bytes()).hexdigest()

    @property
    def label(self) -> str:
        return f"Anlage {self.anlage_nr}"

    @property
    def short_hash(self) -> str:
        return self.sha256[:16] if self.sha256 else "N/A"

    def inline_ref(self) -> str:
        """Compact tag used directly next to a claim, e.g. in Ebene A / Ebene B."""
        parts = [self.label, self.filename]
        if self.page_ref:
            parts.append(f"S. {self.page_ref}")
        if self.sha256:
            parts.append(f"SHA-256: {self.short_hash}…")
        return " · ".join(parts)

    def annex_row(self) -> tuple:
        """Row for the Anlagenverzeichnis table."""
        return (self.label, self.filename, self.description, self.page_ref or "-", f"{self.short_hash}…" if self.sha256 else "N/A")


def build_evidence_index(items: list[EvidenceItem]) -> dict[str, EvidenceItem]:
    """Lookup by Anlage-label, used when Ebene B rows reference an EvidenceItem by label."""
    return {item.label: item for item in items}
