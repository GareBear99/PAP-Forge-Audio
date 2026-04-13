# Contributing to PAP Forge

PAP Forge is built around governed changes, reproducible scaffolds, and explicit receipts.

## Rules

- Do not mutate templates without updating tests.
- Do not add realtime DSP examples that allocate in the audio thread.
- Keep generation deterministic for the same prompt and template.
- Every new CLI command must have at least one focused test.
- Build hooks may fail loudly, but they must emit receipts.

## Workflow

1. Add or modify code.
2. Run `pytest`.
3. Generate at least one effect scaffold and one synth scaffold.
4. Update docs if command surface or manifests changed.
