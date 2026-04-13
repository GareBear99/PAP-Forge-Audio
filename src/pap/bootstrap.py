from __future__ import annotations

import json
import os
from pathlib import Path


def bootstrap_project(project_root: str | Path, *, juce_dir: str | None = None, generator: str = 'Ninja') -> dict[str, object]:
    root = Path(project_root)
    pap_root = root / '.pap'
    pap_root.mkdir(parents=True, exist_ok=True)
    toolchain_dir = pap_root / 'toolchain'
    toolchain_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = pap_root / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    runbooks_dir = pap_root / 'runbooks'
    runbooks_dir.mkdir(parents=True, exist_ok=True)

    resolved_juce = juce_dir or os.environ.get('JUCE_DIR', '')
    payload = {
        'schema': 'pap.toolchain.v1',
        'generator': generator,
        'juce_dir': resolved_juce,
        'juce_dir_exists': bool(resolved_juce and Path(resolved_juce).exists()),
        'project_root': str(root.resolve()),
    }
    toolchain_path = toolchain_dir / 'toolchain.json'
    toolchain_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')

    cmake_user_presets = {
        'version': 3,
        'configurePresets': [
            {
                'name': 'pap-default',
                'displayName': 'PAP Default Configure',
                'generator': generator,
                'binaryDir': '${sourceDir}/.pap/build/default',
                'cacheVariables': {
                    'CMAKE_BUILD_TYPE': 'Release',
                    'JUCE_DIR': resolved_juce,
                },
            }
        ],
        'buildPresets': [
            {
                'name': 'pap-default',
                'configurePreset': 'pap-default',
            }
        ],
    }
    presets_path = root / 'CMakeUserPresets.json'
    presets_path.write_text(json.dumps(cmake_user_presets, indent=2, sort_keys=True), encoding='utf-8')

    local_build = scripts_dir / 'build_local.sh'
    local_build.write_text('\n'.join([
        '#!/usr/bin/env bash',
        'set -euo pipefail',
        'ROOT="$(cd "$(dirname "$0")/../.." && pwd)"',
        'cd "$ROOT"',
        'cmake --preset pap-default',
        'cmake --build --preset pap-default',
    ]) + '\n', encoding='utf-8')
    local_build.chmod(0o755)

    container_build = scripts_dir / 'build_container.sh'
    container_build.write_text('\n'.join([
        '#!/usr/bin/env bash',
        'set -euo pipefail',
        'ROOT="$(cd "$(dirname "$0")/../.." && pwd)"',
        'python "$ROOT/scripts/pap_build_in_container.py" "$ROOT" "${1:-latest}"',
    ]) + '\n', encoding='utf-8')
    container_build.chmod(0o755)

    operator_runbook = runbooks_dir / 'operator_quickstart.md'
    operator_runbook.write_text('\n'.join([
        '# PAP Operator Quickstart',
        '',
        '1. Set `JUCE_DIR` or pass `--juce-dir` during bootstrap.',
        '2. Run `pap doctor <project_root>` to verify tools.',
        '3. Run `pap generate <project_root> "<prompt>"` to create a checkpoint.',
        '4. Run `pap plan <project_root> <checkpoint_id>` to inspect the build plan.',
        '5. Run `.pap/scripts/build_local.sh` for a local build attempt or use the container hook.',
        '6. Use `pap control bind <project_root>` and the `pap control ...` subcommands for runtime control.',
    ]) + '\n', encoding='utf-8')

    return {
        'status': 'ok',
        'toolchain': str(toolchain_path.relative_to(root)),
        'cmake_user_presets': str(presets_path.relative_to(root)),
        'local_build_script': str(local_build.relative_to(root)),
        'container_build_script': str(container_build.relative_to(root)),
        'operator_runbook': str(operator_runbook.relative_to(root)),
    }
