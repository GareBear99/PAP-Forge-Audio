from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re


@dataclass(slots=True)
class PluginSpec:
    plugin_name: str
    vendor_name: str = 'TizWildin Entertainment'
    plugin_type: str = 'effect'
    style_tags: list[str] = field(default_factory=list)
    description: str = ''
    parameters: list[dict[str, object]] = field(default_factory=list)
    dsp_blocks: list[str] = field(default_factory=list)
    macro_controls: list[str] = field(default_factory=list)
    target_formats: list[str] = field(default_factory=lambda: ['VST3'])
    cpu_budget: str = 'moderate'
    template_id: str = 'juce_effect_basic'
    signal_flow: list[str] = field(default_factory=list)
    voice_mode: str = 'none'
    modulation_sources: list[str] = field(default_factory=list)
    validation_profile: str = 'basic'

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


KEYWORD_BLOCKS = {
    'chorus': 'stereo_chorus',
    'delay': 'tempo_delay',
    'reverb': 'hall_reverb',
    'shimmer': 'pitch_shimmer',
    'tape': 'tape_flutter',
    'analog': 'analog_drift',
    'filter': 'state_variable_filter',
    'distortion': 'soft_clip_drive',
    'saturation': 'soft_clip_drive',
    'pad': 'pad_voicing',
    'drift': 'slow_random_mod',
    'compressor': 'rms_compressor',
    'phaser': 'multi_stage_phaser',
    'flanger': 'comb_flanger',
    'oscillator': 'osc_bank',
    'bass': 'sub_voice',
    'lead': 'lead_voice',
    'choir': 'formant_body',
    'granular': 'granular_cloud',
    'ensemble': 'ensemble_spread',
    'detune': 'voice_detune',
    'glide': 'portamento',
}

SYNTH_HINTS = {'synth', 'oscillator', 'poly', 'mono', 'pad', 'lead', 'bass', 'arp', 'pluck'}
LOW_CPU_HINTS = {'low cpu', 'lightweight', 'light weight', 'efficient'}
HIGH_CPU_HINTS = {'oversampled', 'high quality', 'lush', 'cinematic'}
HIGH_VALIDATION_HINTS = {'darpa', 'production', 'release', 'ship'}


def slug_to_name(text: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]+', ' ', text).strip()
    if not cleaned:
        return 'PAPGeneratedPlugin'
    words = cleaned.split()[:5]
    return ''.join(word.capitalize() for word in words)


def infer_plugin_type(lowered: str) -> str:
    if any(hint in lowered for hint in SYNTH_HINTS):
        return 'synth'
    return 'effect'


def infer_cpu_budget(lowered: str) -> str:
    if any(hint in lowered for hint in LOW_CPU_HINTS):
        return 'low'
    if any(hint in lowered for hint in HIGH_CPU_HINTS):
        return 'high'
    return 'moderate'


def infer_template_id(plugin_type: str) -> str:
    return 'juce_synth_basic' if plugin_type == 'synth' else 'juce_effect_basic'


def infer_voice_mode(lowered: str, plugin_type: str) -> str:
    if plugin_type != 'synth':
        return 'none'
    if 'mono' in lowered:
        return 'mono'
    if 'poly' in lowered or 'pad' in lowered:
        return 'poly'
    return 'poly'


def infer_validation_profile(lowered: str) -> str:
    if any(hint in lowered for hint in HIGH_VALIDATION_HINTS):
        return 'production'
    return 'basic'


def spec_from_prompt(prompt: str) -> PluginSpec:
    lowered = prompt.lower()
    plugin_name = slug_to_name(prompt)
    style_tags: list[str] = []
    dsp_blocks: list[str] = []
    macro_controls: list[str] = []
    plugin_type = infer_plugin_type(lowered)
    cpu_budget = infer_cpu_budget(lowered)
    modulation_sources: list[str] = []

    for key, block in KEYWORD_BLOCKS.items():
        if key in lowered:
            style_tags.append(key)
            if block not in dsp_blocks:
                dsp_blocks.append(block)

    macro_match = re.search(r'macro called\s+([A-Za-z0-9_\-]+)', prompt, re.IGNORECASE)
    if macro_match:
        macro_controls.append(macro_match.group(1))

    if 'lfo' in lowered or 'chorus' in lowered or 'phaser' in lowered:
        modulation_sources.append('lfo_1')
    if 'envelope' in lowered or plugin_type == 'synth':
        modulation_sources.append('env_1')
    if 'drift' in lowered or 'analog' in lowered:
        modulation_sources.append('slow_random')

    if not dsp_blocks:
        dsp_blocks = ['gain_stage', 'tone_filter'] if plugin_type == 'effect' else ['osc_bank', 'amp_envelope']
    if not style_tags:
        style_tags = ['custom']

    parameters = [
        {'id': 'mix', 'name': 'Mix', 'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.5},
        {'id': 'output', 'name': 'Output', 'type': 'float', 'min': -24.0, 'max': 24.0, 'default': 0.0},
    ]
    if plugin_type == 'synth':
        parameters = [
            {'id': 'voices', 'name': 'Voices', 'type': 'int', 'min': 1, 'max': 32, 'default': 8},
            {'id': 'attack', 'name': 'Attack', 'type': 'float', 'min': 0.0, 'max': 5.0, 'default': 0.01},
            {'id': 'release', 'name': 'Release', 'type': 'float', 'min': 0.01, 'max': 10.0, 'default': 1.0},
            {'id': 'macro', 'name': 'Macro', 'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.5},
            {'id': 'output', 'name': 'Output', 'type': 'float', 'min': -24.0, 'max': 24.0, 'default': 0.0},
        ]
    if 'chorus' in lowered or 'flanger' in lowered or 'phaser' in lowered:
        parameters.extend([
            {'id': 'rate', 'name': 'Rate', 'type': 'float', 'min': 0.01, 'max': 10.0, 'default': 0.8},
            {'id': 'depth', 'name': 'Depth', 'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.45},
        ])
    if 'reverb' in lowered or 'shimmer' in lowered or 'delay' in lowered:
        parameters.append({'id': 'space', 'name': 'Space', 'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.6})
    if 'tape' in lowered or 'analog' in lowered or 'drift' in lowered:
        parameters.append({'id': 'drift', 'name': 'Drift', 'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.35})
    if plugin_type == 'synth' and 'glide' in lowered:
        parameters.append({'id': 'glide', 'name': 'Glide', 'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.1})
    for macro in macro_controls:
        parameters.append({'id': macro.lower(), 'name': macro, 'type': 'float', 'min': 0.0, 'max': 1.0, 'default': 0.5})

    signal_flow = ['MIDI In' if plugin_type == 'synth' else 'Input'] + [block.replace('_', ' ').title() for block in dsp_blocks] + ['Output']

    return PluginSpec(
        plugin_name=plugin_name,
        description=prompt.strip(),
        plugin_type=plugin_type,
        style_tags=style_tags,
        dsp_blocks=dsp_blocks,
        macro_controls=macro_controls,
        parameters=parameters,
        cpu_budget=cpu_budget,
        signal_flow=signal_flow,
        template_id=infer_template_id(plugin_type),
        voice_mode=infer_voice_mode(lowered, plugin_type),
        modulation_sources=modulation_sources,
        validation_profile=infer_validation_profile(lowered),
    )
