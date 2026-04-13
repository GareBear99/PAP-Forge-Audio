from __future__ import annotations

import json
from pathlib import Path


class ProjectValidator:
    REQUIRED_DIRS = ['.pap']
    REQUIRED_FILES = ['.pap/project.json', '.pap/history.json', '.pap/branches.json']
    GOVERNED_TEMPLATES = {'juce_effect_basic', 'juce_synth_basic'}

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)

    def validate(self) -> dict[str, object]:
        missing: list[str] = []
        warnings: list[str] = []
        for dirname in self.REQUIRED_DIRS:
            if not (self.project_root / dirname).exists():
                missing.append(dirname)
        for rel in self.REQUIRED_FILES:
            if not (self.project_root / rel).exists():
                missing.append(rel)

        spec_path = self.project_root / 'pap' / 'spec.json'
        if not spec_path.exists():
            warnings.append('No generated pap/spec.json present yet.')
        else:
            try:
                spec = json.loads(spec_path.read_text(encoding='utf-8'))
                if spec.get('template_id') not in self.GOVERNED_TEMPLATES:
                    warnings.append('Spec template_id is not one of the governed templates.')
                if not spec.get('parameters'):
                    warnings.append('Spec has no parameters.')
            except json.JSONDecodeError:
                missing.append('pap/spec.json (invalid JSON)')

        for rel in ['pap/template_manifest.json', 'pap/dsp_manifest.json', 'pap/render_manifest.json', 'pap/parameters.json', 'pap/control_manifest.json', 'pap/repro_build_state.json']:
            path = self.project_root / rel
            if spec_path.exists() and not path.exists():
                warnings.append(f'Missing generated support file: {rel}')

        preview_root = self.project_root / '.pap' / 'previews'
        if spec_path.exists() and not preview_root.exists():
            warnings.append('No preview render directory found yet.')

        repro_root = self.project_root / '.pap' / 'reproducible_states'
        if spec_path.exists() and not repro_root.exists():
            warnings.append('No checkpoint reproducible-state directory found yet.')

        return {
            'status': 'ok' if not missing else 'invalid',
            'project_root': str(self.project_root),
            'missing': missing,
            'warnings': warnings,
        }
