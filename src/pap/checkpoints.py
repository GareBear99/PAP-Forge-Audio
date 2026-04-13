from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"cp_{digest}"


@dataclass(slots=True)
class CheckpointManifest:
    checkpoint_id: str
    parent_id: str | None
    created_at: str
    prompt: str
    plugin_name: str
    template_id: str
    project_root: str
    snapshot_dir: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class CheckpointStore:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.meta_dir = self.project_root / ".pap"
        self.snapshots_dir = self.meta_dir / "snapshots"
        self.history_path = self.meta_dir / "history.json"
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.write_text("[]\n", encoding="utf-8")

    def list_checkpoints(self) -> list[dict[str, object]]:
        return json.loads(self.history_path.read_text(encoding="utf-8"))

    def save_checkpoint(self, *, prompt: str, plugin_name: str, template_id: str, parent_id: str | None = None) -> CheckpointManifest:
        created_at = _utcnow()
        checkpoint_id = _make_id(f"{plugin_name}|{created_at}|{prompt}")
        snapshot_dir = self.snapshots_dir / checkpoint_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        for child in self.project_root.iterdir():
            if child.name == ".pap":
                continue
            target = snapshot_dir / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)

        manifest = CheckpointManifest(
            checkpoint_id=checkpoint_id,
            parent_id=parent_id,
            created_at=created_at,
            prompt=prompt,
            plugin_name=plugin_name,
            template_id=template_id,
            project_root=str(self.project_root),
            snapshot_dir=str(snapshot_dir),
        )
        history = self.list_checkpoints()
        history.append(manifest.to_dict())
        self.history_path.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")
        return manifest

    def rollback(self, checkpoint_id: str) -> dict[str, object]:
        history = self.list_checkpoints()
        manifest = next((item for item in history if item["checkpoint_id"] == checkpoint_id), None)
        if manifest is None:
            return {"status": "not_found", "checkpoint_id": checkpoint_id}
        snapshot_dir = Path(manifest["snapshot_dir"])
        if not snapshot_dir.exists():
            return {"status": "missing_snapshot", "checkpoint_id": checkpoint_id}

        for child in list(self.project_root.iterdir()):
            if child.name == ".pap":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

        for child in snapshot_dir.iterdir():
            target = self.project_root / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)
        return {"status": "rolled_back", "checkpoint_id": checkpoint_id}
