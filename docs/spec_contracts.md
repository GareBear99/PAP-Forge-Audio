# PAP Spec Contracts

PAP uses a governed `PluginSpec` as the boundary between natural-language intent and generated plugin workspaces.

## Required fields
- `plugin_name`
- `plugin_type`
- `template_id`
- `parameters`
- `dsp_blocks`
- `signal_flow`

## Stability rule
Any future model or router may improve inference quality, but it must still emit a schema-compatible `PluginSpec` so checkpoint comparison, build planning, and rollback remain deterministic.

## DARPA-grade design intent
This contract exists to keep code generation bounded. Models are allowed to infer intent, not to bypass structure.
