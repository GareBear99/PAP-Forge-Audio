from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .manifests import write_json


def _sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class ReproducibleStateStore:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / '.pap' / 'reproducible_states'
        self.root.mkdir(parents=True, exist_ok=True)

    def _current_path(self) -> Path:
        return self.project_root / 'pap' / 'repro_build_state.json'

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        return self.root / f'{checkpoint_id}.json'

    def list_states(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.root.glob('*.json')):
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
                items.append({
                    'checkpoint_id': payload.get('checkpoint', {}).get('checkpoint_id'),
                    'plugin_name': payload.get('spec', {}).get('plugin_name'),
                    'path': str(path.relative_to(self.project_root)),
                    'schema': payload.get('schema'),
                })
            except json.JSONDecodeError:
                items.append({'checkpoint_id': None, 'plugin_name': None, 'path': str(path.relative_to(self.project_root)), 'schema': 'invalid_json'})
        return items

    def save_state(self, *, checkpoint: dict[str, Any], request: dict[str, Any], spec: dict[str, Any], rendered_files: dict[str, str], branches: dict[str, str | None], current_branch: str, build_plan: dict[str, Any], receipt: dict[str, Any], preview: dict[str, Any], control_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        checkpoint_id = str(checkpoint['checkpoint_id'])
        current_path = self._current_path()
        checkpoint_path = self._checkpoint_path(checkpoint_id)
        generated_files = {}
        generated_files_index = []
        for rel_path, content in sorted(rendered_files.items()):
            digest = _sha1_text(content)
            generated_files[rel_path] = content
            generated_files_index.append({'path': rel_path, 'sha1': digest, 'bytes': len(content.encode('utf-8'))})
        payload: dict[str, Any] = {
            'schema': 'pap.repro_build_state.v1',
            'project_name': self.project_root.name,
            'current_branch': current_branch,
            'checkpoint': checkpoint,
            'request': request,
            'spec': spec,
            'build_plan': build_plan,
            'receipt': receipt,
            'preview': preview,
            'branches': branches,
            'control_manifest': control_manifest,
            'generated_files': generated_files,
            'generated_files_index': generated_files_index,
            'state_paths': {
                'current': str(current_path.relative_to(self.project_root)),
                'checkpoint': str(checkpoint_path.relative_to(self.project_root)),
            },
            'rebuild_contract': {
                'write_mode': 'authoritative_replace_generated_files',
                'rollback_source_of_truth': str(checkpoint_path.relative_to(self.project_root)),
                'copyable_json': True,
                'restorable_via_cli': True,
            },
        }
        write_json(current_path, payload)
        write_json(checkpoint_path, payload)
        return {
            'schema': payload['schema'],
            'checkpoint_id': checkpoint_id,
            'current_path': str(current_path.relative_to(self.project_root)),
            'checkpoint_path': str(checkpoint_path.relative_to(self.project_root)),
            'generated_file_count': len(generated_files),
        }

    def load_state(self, path_or_checkpoint: str | Path | None = None) -> dict[str, Any]:
        if path_or_checkpoint is None:
            path = self._current_path()
        else:
            candidate = Path(path_or_checkpoint)
            if candidate.exists():
                path = candidate
            else:
                value = str(path_or_checkpoint)
                if value.startswith('cp_'):
                    path = self._checkpoint_path(value)
                else:
                    path = self.project_root / value
        return json.loads(path.read_text(encoding='utf-8'))

    def apply_state(self, path_or_checkpoint: str | Path | None = None) -> dict[str, Any]:
        state = self.load_state(path_or_checkpoint)
        files = state.get('generated_files', {})
        if not isinstance(files, dict) or not files:
            raise ValueError('Reproducible state has no generated_files payload.')
        for child in list(self.project_root.iterdir()):
            if child.name == '.pap':
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        for rel_path, content in sorted(files.items()):
            target = self.project_root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding='utf-8')
        current_snapshot = self._current_path()
        write_json(current_snapshot, state)
        cp_id = state.get('checkpoint', {}).get('checkpoint_id')
        if cp_id:
            write_json(self._checkpoint_path(str(cp_id)), state)
        return {
            'status': 'applied',
            'checkpoint_id': cp_id,
            'written_files': sorted(files.keys()),
            'state_path': str(current_snapshot.relative_to(self.project_root)),
        }
