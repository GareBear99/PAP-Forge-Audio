# Reproducible build state

PAP now emits a canonical JSON build-state artifact for every checkpoint.

## Files
- `pap/repro_build_state.json`
- `.pap/reproducible_states/<checkpoint_id>.json`

## Purpose
These JSON files are the reproducible rollback and rebuild source of truth for generated plugin states.

## Contents
- request
- spec
- checkpoint
- branches
- build_plan
- receipt
- preview
- control_manifest
- generated_files
- generated_files_index

## CLI
```bash
PYTHONPATH=src python -m pap.cli state <project_root>
PYTHONPATH=src python -m pap.cli state-list <project_root>
PYTHONPATH=src python -m pap.cli state-apply <project_root> <checkpoint_id|state_json_path>
```
