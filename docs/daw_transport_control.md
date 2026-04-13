# PAP DAW Transport Control

PAP v1.1 adds a richer control/runtime bridge for driving generated plugins from the terminal or UDP JSON.

## Runtime state

The generated plugin bridge polls:

- `.pap/control/runtime_state.json`

The state now includes:

- `parameters`
- `midi`
- `transport`
- `markers`

## CLI examples

```bash
pap control transport <project_root> --playing true --bpm 128 --bar 17 --beat 1
pap control marker <project_root> chorus_drop --position-beats 64 --color purple
pap control snapshot-save <project_root> pre_drop
pap control monitor <project_root> --count 4 --interval 0.05
pap control clear-midi <project_root>
```

## UDP JSON examples

```json
{"address": "/pap/transport", "value": {"playing": true, "bpm": 128.0, "bar": 9, "beat": 1}}
```

```json
{"address": "/pap/marker", "value": {"name": "drop", "position_beats": 64.0, "color": "purple"}}
```

## Reaper helper

Each generated project also emits a starter ReaScript bridge under:

- `pap/bridges/reaper/PapReaperBridge.py`

It is a minimal helper that writes PAP runtime-state updates from Reaper's Python scripting environment.
