# PAP CLI Control Runtime

PAP supports two runtime control paths for generated plugins:

1. **File bridge:** the plugin polls `.pap/control/runtime_state.json` from inside `processBlock`.
2. **UDP bridge:** `pap control serve` listens for OSC-like UDP JSON packets and converts them into runtime-state updates.

## Control commands

- `pap control bind <project_root>`
- `pap control set <project_root> <parameter_id> <value>`
- `pap control batch <project_root> <json_path>`
- `pap control note <project_root> <on|off> <note> <velocity>`
- `pap control panic <project_root>`
- `pap control preset-save <project_root> <name>`
- `pap control preset-load <project_root> <name>`
- `pap control automation <project_root> <timeline.json>`
- `pap control serve <project_root>`
- `pap control export-shell <project_root>`

## UDP packet shape

```json
{"address": "/pap/param/mix", "value": 0.72}
```

```json
{"address": "/pap/note/on", "value": {"note": 60, "velocity": 100, "channel": 1}}
```

## Timeline automation shape

```json
[
  {"at": 0.0, "kind": "set", "parameter_id": "mix", "value": 0.25},
  {"at": 0.5, "kind": "batch", "values": {"mix": 0.70, "depth": 0.45}},
  {"at": 1.0, "kind": "note", "event_type": "on", "note": 60, "velocity": 100, "channel": 1},
  {"at": 1.5, "kind": "panic"}
]
```
