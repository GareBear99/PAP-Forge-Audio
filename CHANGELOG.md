## 1.5.0

- Added compact runtime UI generation for JUCE-ready PAP plugins.
- Added `pap/ui_manifest.json` and `Source/PapUiRuntime.h`.
- Upgraded generated plugin editors to show primary controls, runtime badges, and signal flow in a compact layout.
- Added `pap ui <project_root>` to inspect the generated UI manifest quickly.

## 1.3.0

- Added canonical JSON reproducible build-state emission for every generated checkpoint.
- Added `pap state`, `pap state-list`, and `pap state-apply` commands.
- Added current-head `pap/repro_build_state.json` and immutable `.pap/reproducible_states/<checkpoint_id>.json` outputs.
- Added generated-file checksums and full generated payload capture inside reproducible-state JSON.
- Export/release flows now report reproducible-state coverage.

## 1.2.0

- Added `pap bootstrap` for toolchain/bootstrap scaffolding per project.
- Added `pap report` to emit a markdown operator report.
- Doctor now checks `ninja` and whether `JUCE_DIR` actually exists.
- Project bootstrap now writes `CMakeUserPresets.json`, local/container build helper scripts, and an operator quickstart runbook.

# Changelog

## 0.9.0
- added CLI / DAW control surface
- added control manifest generation
- added runtime control state, presets, and session binding
- added generated JUCE `PapCliControl` bridge files
- added control commands for parameter set, batch, note, panic, preset save/load

0.8.0
- Added offline preview WAV rendering per checkpoint
- Added release packaging and doctor flow
- Added current-head and prompt-history manifests
- Upgraded generated templates to more credible JUCE-ready source
- Added generated parameter source files and preset snapshots
- Upgraded build plans toward concrete cmake build attempts when JUCE_DIR is set


## 1.1.0

- Added UDP control daemon for OSC-like CLI-to-DAW bridge operation.
- Added timed automation playback from JSON timelines.
- Added control environment export shell script generation.
- Hardened control-state writes with atomic file replacement.
- Promoted repo version to 1.1.0.
