from __future__ import annotations

import json
from pathlib import Path


class CheckpointComparator:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.snapshot_root = self.project_root / '.pap' / 'snapshots'

    def compare(self, left: str, right: str) -> dict[str, object]:
        left_root = self.snapshot_root / left
        right_root = self.snapshot_root / right
        if not left_root.exists() or not right_root.exists():
            missing = []
            if not left_root.exists():
                missing.append(left)
            if not right_root.exists():
                missing.append(right)
            return {'status': 'missing', 'missing': missing}

        left_files = {p.relative_to(left_root).as_posix(): p for p in left_root.rglob('*') if p.is_file()}
        right_files = {p.relative_to(right_root).as_posix(): p for p in right_root.rglob('*') if p.is_file()}
        added = sorted(set(right_files) - set(left_files))
        removed = sorted(set(left_files) - set(right_files))
        changed: list[str] = []
        for rel in sorted(set(left_files) & set(right_files)):
            if left_files[rel].read_bytes() != right_files[rel].read_bytes():
                changed.append(rel)

        spec_delta = None
        left_spec = left_root / 'pap' / 'spec.json'
        right_spec = right_root / 'pap' / 'spec.json'
        if left_spec.exists() and right_spec.exists():
            spec_delta = {
                'left_plugin_name': json.loads(left_spec.read_text(encoding='utf-8')).get('plugin_name'),
                'right_plugin_name': json.loads(right_spec.read_text(encoding='utf-8')).get('plugin_name'),
            }

        return {
            'status': 'ok',
            'left': left,
            'right': right,
            'added': added,
            'removed': removed,
            'changed': changed,
            'spec_delta': spec_delta,
        }
