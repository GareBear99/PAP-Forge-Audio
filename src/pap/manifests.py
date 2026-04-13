from __future__ import annotations

import json
from pathlib import Path


def write_json(path: str | Path, payload: dict | list) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    return target


def project_status_manifest(*, project_name: str, branches: dict[str, str | None], checkpoints: list[dict[str, object]], validation: dict[str, object] | None = None) -> dict[str, object]:
    latest = checkpoints[-1] if checkpoints else None
    return {
        'project_name': project_name,
        'checkpoint_count': len(checkpoints),
        'branches': branches,
        'latest_checkpoint': latest,
        'validation': validation,
    }
