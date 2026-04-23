> 🎛️ Part of the [TizWildin Plugin Ecosystem](https://garebear99.github.io/TizWildinEntertainmentHUB/) — 16 free audio plugins with a live update dashboard.
>
> [FreeEQ8](https://github.com/GareBear99/FreeEQ8) · [XyloCore](https://github.com/GareBear99/XyloCore) · [Instrudio](https://github.com/GareBear99/Instrudio) · [Therum](https://github.com/GareBear99/Therum_JUCE-Plugin) · [BassMaid](https://github.com/GareBear99/BassMaid) · [SpaceMaid](https://github.com/GareBear99/SpaceMaid) · [GlueMaid](https://github.com/GareBear99/GlueMaid) · [MixMaid](https://github.com/GareBear99/MixMaid) · [ChainMaid](https://github.com/GareBear99/ChainMaid) · [PaintMask](https://github.com/GareBear99/PaintMask_Free-JUCE-Plugin) · [WURP](https://github.com/GareBear99/WURP_Toxic-Motion-Engine_JUCE) · [AETHER](https://github.com/GareBear99/AETHER_Choir-Atmosphere-Designer) · [WhisperGate](https://github.com/GareBear99/WhisperGate_Free-JUCE-Plugin) · [RiftWave](https://github.com/GareBear99/RiftWaveSuite_RiftSynth_WaveForm_Lite) · [FreeSampler](https://github.com/GareBear99/FreeSampler_v0.3) · [VF-PlexLab](https://github.com/GareBear99/VF-PlexLab) · [PAP-Forge-Audio](https://github.com/GareBear99/PAP-Forge-Audio)
>
> 🎁 [Free Packs & Samples](#tizwildin-free-sample-packs) — jump to free packs & samples
>
> 🎵 [Awesome Audio](https://github.com/GareBear99/awesome-audio-plugins-dev) — (FREE) Awesome Audio Dev List

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

## TizWildin FREE sample packs

| Pack | Description |
|------|-------------|
| [**TizWildin-Aurora**](https://github.com/GareBear99/TizWildin-Aurora) | 3-segment original synth melody pack with loops, stems, demo renders, and neon/cinematic phrasing |
| [**TizWildin-Obsidian**](https://github.com/GareBear99/TizWildin-Obsidian) | Dark cinematic sample pack with choir textures, menu loops, transitions, bass, atmosphere, drums, and electric-banjo extensions |
| [**TizWildin-Skyline**](https://github.com/GareBear99/TizWildin-Skyline) | 30 BPM-tagged synthwave and darkwave loops with generator snapshot and dark neon additions |
| [**TizWildin-Chroma**](https://github.com/GareBear99/TizWildin-Chroma) | Multi-segment game synthwave loop sample pack from TizWildin Entertainment |
| [**TizWildin-Chime**](https://github.com/GareBear99/TizWildin-Chime) | Multi-part 88 BPM chime collection spanning glass, void, halo, reed, and neon synthwave lanes |
| [**Free Violin Synth Sample Kit**](https://github.com/GareBear99/Free-Violin-Synth-Sample-Kit) | Physical-model violin sample kit rendered from the Instrudio violin instrument |
| [**Free Dark Piano Sound Kit**](https://github.com/GareBear99/Free-Dark-Piano-Sound-Kit) | 88 piano notes + dark/cinematic loops and MIDI |
| [**Free 808 Producer Kit**](https://github.com/GareBear99/Free-808-Producer-Kit) | 94 hand-crafted 808 bass samples tuned to every chromatic key |
| [**Free Riser Producer Kit**](https://github.com/GareBear99/Free-Riser-Producer-Kit) | 115+ risers and 63 downlifters - noise, synth, drum, FX, cinematic |
| [**Phonk Producer Toolkit**](https://github.com/GareBear99/Phonk_Producer_Toolkit) | Drift phonk starter kit - 808s, cowbells, drums, MIDI, templates |
| [**Free Future Bass Producer Kit**](https://github.com/GareBear99/Free-Future-Bass-Producer-Kit) | Loops, fills, drums, bass, synths, pads, and FX |

### Related audio projects
- [**VF-PlexLab**](https://github.com/GareBear99/VF-PlexLab) - VocalForge PersonaPlex Lab starter repo for a JUCE plugin + local backend + HTML tester around NVIDIA PersonaPlex.
- [**PAP-Forge-Audio**](https://github.com/GareBear99/PAP-Forge-Audio) - Procedural Autonomous Plugins runtime for generating, branching, validating, and restoring plugin projects from natural-language sound intent.

