from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

from .contracts import ArtifactRecord


class ArtifactStore:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / ".pap" / "artifacts"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sha1_bytes(data: bytes) -> str:
        return hashlib.sha1(data).hexdigest()

    def record_text(self, checkpoint_id: str, rel_path: str, content: str) -> ArtifactRecord:
        data = content.encode("utf-8")
        digest = self._sha1_bytes(data)
        target = self.root / checkpoint_id / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return ArtifactRecord(
            kind="generated_text",
            path=str(target.relative_to(self.project_root)),
            checksum=digest,
            bytes_size=len(data),
        )

    def snapshot_file(self, checkpoint_id: str, source: str | Path, *, kind: str = "file") -> ArtifactRecord:
        source_path = Path(source)
        data = source_path.read_bytes()
        digest = self._sha1_bytes(data)
        target = self.root / checkpoint_id / source_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        return ArtifactRecord(
            kind=kind,
            path=str(target.relative_to(self.project_root)),
            checksum=digest,
            bytes_size=len(data),
        )
