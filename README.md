# PAP Forge

**PAP — Procedural Autonomous Plugins**

PAP Forge is a governed runtime for generating, checkpointing, branching, mutating, previewing, releasing, exporting, comparing, validating, and restoring plugin projects from natural-language sound intent.

This version adds a canonical **JSON reproducible build-state** layer so every checkpoint can be copied, saved, reapplied, and rebuilt from a single source-of-truth JSON file alongside the CLI/DAW control surface.

## What it does

- initializes PAP projects
- infers plugin specs from prompts
- routes prompts to effect or synth scaffolds
- renders JUCE-ready project files
- emits generated parameter, DSP, signal-graph, and CLI-control source files
- checkpoints every generation
- tracks branch heads and prompt lineage
- stores generated-file artifacts with checksums
- renders an offline preview WAV per checkpoint
- emits build plans and build execution receipts
- validates project structure and spec integrity
- compares checkpoints
- exports restorable bundles and release archives
- emits canonical JSON reproducible build states per checkpoint and for the current head
- exposes an optional FastAPI service layer
- exposes a **CLI control plane** for parameter writes, note events, panic, preset save/load, and control-session binding

## CLI

```bash
PYTHONPATH=src python -m pap.cli init demo workspace
PYTHONPATH=src python -m pap.cli bootstrap workspace/demo --juce-dir /path/to/JUCE
PYTHONPATH=src python -m pap.cli generate workspace/demo "Dark shimmer chorus with macro called Collapse"
PYTHONPATH=src python -m pap.cli control bind workspace/demo
PYTHONPATH=src python -m pap.cli control set workspace/demo mix 0.72
PYTHONPATH=src python -m pap.cli control batch workspace/demo control_patch.json
PYTHONPATH=src python -m pap.cli control note workspace/demo on 60 100 --channel 1
PYTHONPATH=src python -m pap.cli control panic workspace/demo
PYTHONPATH=src python -m pap.cli control preset-save workspace/demo verse_a
PYTHONPATH=src python -m pap.cli control preset-load workspace/demo verse_a
PYTHONPATH=src python -m pap.cli state workspace/demo
PYTHONPATH=src python -m pap.cli state workspace/demo cp_xxxxx
PYTHONPATH=src python -m pap.cli state-list workspace/demo
PYTHONPATH=src python -m pap.cli state-apply workspace/demo cp_xxxxx
```

## DAW / plugin CLI control path

Each generated plugin project now includes:

- `pap/control_manifest.json`
- `Source/PapCliControl.h`
- `Source/PapCliControl.cpp`

The generated JUCE plugin polls a shared state file:

- `.pap/control/runtime_state.json`

You can point the plugin at a specific state file with:

- `PAP_CONTROL_STATE_FILE=/absolute/path/to/runtime_state.json`

The CLI writes parameter and MIDI-style events into that file. The generated plugin bridge applies:

- parameter updates through APVTS
- synth note on/off events through `MidiBuffer`
- panic/all-notes-off events

Optional UDP OSC-like messages are also emitted when `--osc` is used.

## What this repo still does not honestly claim

- bundled JUCE source vendoring out of the box
- guaranteed turnkey VST3/AU/CLAP binaries without your toolchains
- complete realtime-safe DSP generation from arbitrary prompts
- perceptual audio-quality scoring against references
- mature symbol-grounded autonomous editing inside a large live JUCE codebase

## Repo layout

- `src/pap/project.py` — orchestration layer
- `src/pap/specs.py` — prompt normalization into plugin specs
- `src/pap/templates.py` — template routing and rendering
- `src/pap/control.py` — CLI control surface and runtime-state writer
- `src/pap/preview.py` — offline checkpoint audio preview rendering
- `src/pap/checkpoints.py` — snapshot store and rollback
- `src/pap/builds.py` — build plans and execution receipts
- `templates/juce_effect_basic/` — governed effect scaffold
- `templates/juce_synth_basic/` — governed synth scaffold


## CLI control and DAW bridge

PAP can be driven from the terminal while the generated plugin is open in a DAW.
The generated JUCE project includes `PapCliControl.*`, which polls `.pap/control/runtime_state.json`.

Typical operator flow:

```bash
PYTHONPATH=src python -m pap.cli control bind <project_root>
PYTHONPATH=src python -m pap.cli control export-shell <project_root>
source <project_root>/.pap/control/pap_control_env.sh
PYTHONPATH=src python -m pap.cli control set <project_root> mix 0.72
PYTHONPATH=src python -m pap.cli control note <project_root> on 60 100
```

UDP bridge mode is also available:

```bash
PYTHONPATH=src python -m pap.cli control serve <project_root> --host 127.0.0.1 --port 9031
PYTHONPATH=src python -m pap.cli control set <project_root> mix 0.85 --osc
```

Timed automation playback from JSON:

```json
[
  {"at": 0.0, "kind": "set", "parameter_id": "mix", "value": 0.35},
  {"at": 0.5, "kind": "set", "parameter_id": "mix", "value": 0.80},
  {"at": 1.0, "kind": "note", "event_type": "on", "note": 60, "velocity": 100}
]
```

```bash
PYTHONPATH=src python -m pap.cli control automation <project_root> timeline.json --speed 1.0
```

## Operator bootstrap and reporting

```bash
PYTHONPATH=src python -m pap.cli bootstrap workspace/demo --juce-dir /path/to/JUCE
PYTHONPATH=src python -m pap.cli doctor workspace/demo
PYTHONPATH=src python -m pap.cli report workspace/demo
```

## JSON reproducible build state

Every generated checkpoint now emits two authoritative JSON files:

- `pap/repro_build_state.json` — current-head reproducible build state
- `.pap/reproducible_states/<checkpoint_id>.json` — immutable checkpoint reproducible state

Each JSON state carries:
- prompt and generation request
- normalized plugin spec
- checkpoint metadata
- branch heads at generation time
- build-plan metadata
- receipt metadata
- preview metadata
- control-manifest metadata
- full generated source/file payloads
- per-file checksums for the generated payloads

That means you can:
- copy a single JSON file and keep the whole reproducible plugin state
- reapply that state into a PAP project with `state-apply`
- use the JSON file itself as the rollback/rebuild source of truth

Typical flow:

```bash
PYTHONPATH=src python -m pap.cli generate workspace/demo "Dark shimmer chorus with macro called Collapse"
PYTHONPATH=src python -m pap.cli state workspace/demo
PYTHONPATH=src python -m pap.cli state-list workspace/demo
PYTHONPATH=src python -m pap.cli state-apply workspace/demo .pap/reproducible_states/<checkpoint_id>.json
```


## Features
- Compact runtime UI generation for JUCE-ready plugins
- Instantly understandable primary-controls layout with runtime and signal-flow cards
