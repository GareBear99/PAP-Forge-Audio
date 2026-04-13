# CLI / DAW Control

PAP v0.9 adds a control plane intended for terminal-driven automation of generated plugin projects.

## Control modes

1. **Shared state file**
   - CLI writes `.pap/control/runtime_state.json`
   - generated plugin bridge polls this file inside `processBlock`

2. **Optional UDP OSC-like mirror**
   - enabled per command with `--osc`
   - sends JSON payloads to the bound host/port

## Main commands

```bash
pap control bind <project_root> [checkpoint_id] [--host 127.0.0.1] [--port 9031]
pap control status <project_root>
pap control set <project_root> <parameter_id> <value> [--osc]
pap control batch <project_root> <json_path> [--osc]
pap control note <project_root> <on|off> <note> <velocity> [--channel N] [--osc]
pap control panic <project_root> [--osc]
pap control preset-save <project_root> <name>
pap control preset-load <project_root> <name> [--osc]
```

## Runtime state schema

```json
{
  "schema": "pap.control.v1",
  "event_id": 4,
  "plugin_name": "Pap Dark Shimmer Chorus",
  "checkpoint_id": "cp_0004",
  "parameters": {"mix": 0.72, "output": -3.0},
  "transport": {"panic": false},
  "midi": [{"type": "on", "note": 60, "velocity": 100, "channel": 1}]
}
```

## Generated plugin bridge

Generated projects include `Source/PapCliControl.*`, which:

- loads the runtime state file
- applies APVTS parameter writes
- injects synth note events into `MidiBuffer`
- reacts to panic/all-notes-off

This is the repo’s current terminal-to-plugin control path.
