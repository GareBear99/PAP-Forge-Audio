# PAP Compact Plugin UI Runtime

PAP v1.5.0 emits a compact JUCE-ready plugin editor focused on instant readability.

## Layout
- Header card with plugin name, plugin type, and layout mode
- Runtime badges for runtime readiness and CLI bridge live status
- Primary Controls card with up to 6 important rotary controls
- Signal Flow footer showing the generated processing chain

## Generated assets
- `pap/ui_manifest.json`
- `Source/PapUiRuntime.h`
- upgraded `Source/PluginEditor.h/.cpp`

## Goal
The first impression should be simple: open the plugin and immediately see what it is, what matters most, and whether the PAP runtime bridge is active.
