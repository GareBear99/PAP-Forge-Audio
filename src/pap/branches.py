from __future__ import annotations

import json
from pathlib import Path


class BranchStore:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.path = self.project_root / ".pap" / "branches.json"
        if not self.path.exists():
            self.path.write_text(json.dumps({"main": None}, indent=2, sort_keys=True), encoding="utf-8")

    def _read(self) -> dict[str, str | None]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, str | None]) -> None:
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def list_branches(self) -> dict[str, str | None]:
        return self._read()

    def head(self, branch_name: str = "main") -> str | None:
        return self._read().get(branch_name)

    def update_head(self, checkpoint_id: str, branch_name: str = "main") -> None:
        payload = self._read()
        payload[branch_name] = checkpoint_id
        self._write(payload)

    def create_branch(self, branch_name: str, from_checkpoint_id: str | None) -> dict[str, object]:
        payload = self._read()
        if branch_name in payload:
            return {"status": "exists", "branch": branch_name, "head": payload[branch_name]}
        payload[branch_name] = from_checkpoint_id
        self._write(payload)
        return {"status": "created", "branch": branch_name, "head": from_checkpoint_id}
