# PAP Forge Architecture

PAP Forge is a governed system for Procedural Autonomous Plugins.

## Pipeline

1. Prompt -> structured spec
2. Spec -> template selection
3. Template render -> project workspace
4. Preview render -> checkpoint audition artifact
5. Checkpoint snapshot -> immutable restore point
6. Artifact capture -> generated file receipts
7. Build plan -> declared container action
8. Release/export -> distributable handoff package
9. Branch head update -> lineage control

## Core modules

- `pap.specs`: natural-language normalization
- `pap.templates`: template routing + rendering
- `pap.preview`: offline checkpoint audition renders
- `pap.project`: orchestration
- `pap.checkpoints`: snapshots + rollback
- `pap.branches`: branch heads
- `pap.artifacts`: file receipts
- `pap.builds`: build plans + build receipts
- `pap.graph`: lineage graph emission
- `pap.manifests`: project status and export manifests
- `pap.validators`: repo-level validation

## Product truth

This repo is a serious governed runtime and handoff package. It still does not claim to be a finished universal compiler-backed audio product, but it now includes the repo contracts, release surface, preview layer, and operator flow expected before that phase starts.
