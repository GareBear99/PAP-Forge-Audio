from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from string import Template

from .specs import PluginSpec


@dataclass(slots=True)
class RenderedTemplate:
    template_id: str
    files: dict[str, str]


class TemplateLibrary:
    def __init__(self, template_root: str | Path) -> None:
        self.template_root = Path(template_root)

    def _root_for_template(self, template_id: str) -> Path:
        candidate = self.template_root.parent / template_id
        if not candidate.exists():
            raise ValueError(f'Unsupported template: {template_id}')
        return candidate

    def render(self, spec: PluginSpec) -> RenderedTemplate:
        root = self._root_for_template(spec.template_id)
        files: dict[str, str] = {}
        substitutions = {
            'plugin_name': spec.plugin_name,
            'vendor_name': spec.vendor_name,
            'description': spec.description,
            'plugin_type': spec.plugin_type,
            'cpu_budget': spec.cpu_budget,
            'dsp_blocks': ', '.join(spec.dsp_blocks),
            'style_tags': ', '.join(spec.style_tags),
            'macro_controls': ', '.join(spec.macro_controls) or 'none',
            'signal_flow': ' -> '.join(spec.signal_flow),
            'voice_mode': spec.voice_mode,
            'modulation_sources': ', '.join(spec.modulation_sources) or 'none',
            'validation_profile': spec.validation_profile,
            'parameter_layout_cpp': self._parameter_layout_cpp(spec),
            'parameter_member_cpp': self._parameter_member_cpp(spec),
        }
        for path in root.rglob('*'):
            if path.is_dir():
                continue
            rel = path.relative_to(root).as_posix()
            text = path.read_text(encoding='utf-8')
            files[rel] = Template(text).safe_substitute(substitutions)

        files['pap/spec.json'] = spec.to_json()
        files['pap/signal_flow.txt'] = substitutions['signal_flow'] + '\n'
        files['pap/template_manifest.json'] = json.dumps({
            'template_id': spec.template_id,
            'plugin_name': spec.plugin_name,
            'voice_mode': spec.voice_mode,
            'validation_profile': spec.validation_profile,
            'modulation_sources': spec.modulation_sources,
        }, indent=2) + '\n'
        files['pap/parameters.json'] = json.dumps({'plugin_name': spec.plugin_name, 'parameters': spec.parameters}, indent=2) + '\n'
        files['pap/dsp_manifest.json'] = json.dumps({
            'plugin_name': spec.plugin_name,
            'plugin_type': spec.plugin_type,
            'dsp_blocks': spec.dsp_blocks,
            'signal_flow': spec.signal_flow,
            'cpu_budget': spec.cpu_budget,
        }, indent=2) + '\n'
        files['pap/render_manifest.json'] = json.dumps({
            'plugin_name': spec.plugin_name,
            'preview_strategy': 'offline_python_renderer',
            'plugin_type': spec.plugin_type,
            'style_tags': spec.style_tags,
        }, indent=2) + '\n'
        files['pap/dsp_contract.md'] = self._dsp_contract(spec)
        files['pap/preset_snapshot.json'] = json.dumps({
            'plugin_name': spec.plugin_name,
            'checkpoint_defaults': {p['id']: p['default'] for p in spec.parameters},
        }, indent=2) + '\n'
        files['pap/control_manifest.json'] = json.dumps({
            'schema': 'pap.control_manifest.v2',
            'plugin_name': spec.plugin_name,
            'plugin_type': spec.plugin_type,
            'state_file': '.pap/control/runtime_state.json',
            'parameters': spec.parameters,
            'midi_supported': spec.plugin_type == 'synth',
            'transport_supported': True,
            'osc': {
                'parameter_prefix': '/pap/param/',
                'note_prefix': '/pap/note/',
                'panic_address': '/pap/panic',
                'transport_address': '/pap/transport',
                'marker_address': '/pap/marker',
            },
        }, indent=2) + '\n'
        files['pap/bridges/README.md'] = self._bridges_readme(spec)
        files['pap/bridges/reaper/PapReaperBridge.py'] = self._reaper_bridge_script(spec)
        files['Source/PapDSPBlocks.h'] = self._dsp_blocks_header(spec)
        files['Source/PapSignalGraph.h'] = self._signal_graph_header(spec)
        files['Source/PapProcessPlan.cpp'] = self._process_plan_cpp(spec)
        files['Source/PapGeneratedParameters.h'] = self._generated_parameters_header(spec)
        files['Source/PapGeneratedParameters.cpp'] = self._generated_parameters_cpp(spec)
        files['Source/PapCliControl.h'] = self._cli_control_header()
        files['Source/PapCliControl.cpp'] = self._cli_control_cpp()
        return RenderedTemplate(template_id=spec.template_id, files=files)

    def _parameter_layout_cpp(self, spec: PluginSpec) -> str:
        entries = []
        for p in spec.parameters:
            pid = p['id']
            name = p['name']
            if p['type'] == 'int':
                entries.append(f'    layout.add(std::make_unique<juce::AudioParameterInt>(juce::ParameterID{{"{pid}", 1}}, "{name}", {int(p["min"])}, {int(p["max"])}, {int(p["default"])}));')
            else:
                entries.append(f'    layout.add(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID{{"{pid}", 1}}, "{name}", juce::NormalisableRange<float>({float(p["min"]):.4f}f, {float(p["max"]):.4f}f), {float(p["default"]):.4f}f));')
        return '\n'.join(entries)

    def _parameter_member_cpp(self, spec: PluginSpec) -> str:
        return '\n'.join(f'    float {p["id"]} = {float(p["default"]):.4f}f;' for p in spec.parameters)

    def _dsp_contract(self, spec: PluginSpec) -> str:
        block_lines = '\n'.join(f'- `{block}`' for block in spec.dsp_blocks)
        param_lines = '\n'.join(f'- `{p["id"]}` ({p["type"]}) default `{p["default"]}`' for p in spec.parameters)
        return f'''# PAP DSP Contract\n\n**Plugin:** {spec.plugin_name}\n\n**Type:** {spec.plugin_type}\n\n**Signal flow:** {' -> '.join(spec.signal_flow)}\n\n## Blocks\n{block_lines}\n\n## Parameters\n{param_lines}\n'''

    def _bridges_readme(self, spec: PluginSpec) -> str:
        return f'''# PAP DAW Bridges\n\nThis project exposes a file/UDP control bridge for **{spec.plugin_name}**.\n\n## Runtime files\n- `.pap/control/runtime_state.json`\n- `.pap/control/session.json`\n\n## UDP JSON addresses\n- `/pap/param/<parameter_id>`\n- `/pap/params`\n- `/pap/note/on`\n- `/pap/note/off`\n- `/pap/panic`\n- `/pap/transport`\n- `/pap/marker`\n- `/pap/snapshot/save`\n- `/pap/snapshot/load`\n\n## Reaper helper\nA starter ReaScript is provided under `pap/bridges/reaper/PapReaperBridge.py`.\n'''

    def _reaper_bridge_script(self, spec: PluginSpec) -> str:
        return f'''# PAP Reaper bridge starter for {spec.plugin_name}\n# Run inside Reaper's Python ReaScript environment.\n# This script writes CLI-control state so the generated PAP plugin can react.\n\nimport json\nimport os\nimport time\n\nPAP_STATE = os.environ.get("PAP_CONTROL_STATE_FILE", ".pap/control/runtime_state.json")\n\ndef write_param(param_id, value):\n    try:\n        with open(PAP_STATE, "r", encoding="utf-8") as fh:\n            payload = json.load(fh)\n    except FileNotFoundError:\n        payload = {{\n            "schema": "pap.control.v2",\n            "event_id": 0,\n            "parameters": {{}},\n            "midi": [],\n            "transport": {{"panic": False, "playing": False, "bpm": 120.0}},\n        }}\n    payload.setdefault("parameters", {{}})[param_id] = float(value)\n    payload["event_id"] = int(payload.get("event_id", 0)) + 1\n    payload["updated_at"] = time.time()\n    tmp = PAP_STATE + ".tmp"\n    with open(tmp, "w", encoding="utf-8") as fh:\n        json.dump(payload, fh, indent=2, sort_keys=True)\n    os.replace(tmp, PAP_STATE)\n\n# Example:\nwrite_param("mix", 0.75)\n'''

    def _dsp_blocks_header(self, spec: PluginSpec) -> str:
        blocks = ', '.join(spec.dsp_blocks)
        return f'''#pragma once\n\n#include <JuceHeader.h>\n\nnamespace pap\n{{\nstruct GeneratedState\n{{\n{self._parameter_member_cpp(spec)}\n}};\n\ninline float applyOutputGain(float sample, float outputDb)\n{{\n    return sample * juce::Decibels::decibelsToGain(outputDb);\n}}\n\ninline const char* getPapBlocks() noexcept\n{{\n    return "{blocks}";\n}}\n}}\n'''

    def _signal_graph_header(self, spec: PluginSpec) -> str:
        flow = ' -> '.join(spec.signal_flow)
        return f'''#pragma once\n\nnamespace pap\n{{\ninline const char* getPapSignalGraph() noexcept\n{{\n    return "{flow}";\n}}\n}}\n'''

    def _process_plan_cpp(self, spec: PluginSpec) -> str:
        comments = '\n'.join(f'//  - {b}' for b in spec.dsp_blocks)
        return f'''#include "PapDSPBlocks.h"\n#include "PapSignalGraph.h"\n\n/*\n Prompt-derived process plan for {spec.plugin_name}\n {comments}\n CLI control path: .pap/control/runtime_state.json and /pap/* OSC-style addresses\n*/\n'''

    def _generated_parameters_header(self, spec: PluginSpec) -> str:
        return '''#pragma once\n\n#include <JuceHeader.h>\n\nnamespace pap\n{\njuce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();\n}\n'''

    def _generated_parameters_cpp(self, spec: PluginSpec) -> str:
        return f'''#include "PapGeneratedParameters.h"\n\nnamespace pap\n{{\njuce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout()\n{{\n    juce::AudioProcessorValueTreeState::ParameterLayout layout;\n{substituted_parameter_layout(self._parameter_layout_cpp(spec))}\n    return layout;\n}}\n}}\n'''

    def _cli_control_header(self) -> str:
        return '''#pragma once\n\n#include <JuceHeader.h>\n\nnamespace pap\n{\nclass CliControlBridge\n{\npublic:\n    CliControlBridge();\n    void pollAndApply(juce::AudioProcessorValueTreeState& parameters, juce::MidiBuffer* midi = nullptr);\n\nprivate:\n    juce::File stateFile;\n    juce::Time lastStamp;\n    int lastEventId = -1;\n\n    void applyParameterObject(const juce::var& parameterObject, juce::AudioProcessorValueTreeState& parameters);\n    void applyMidiArray(const juce::var& midiArray, juce::MidiBuffer* midi);\n};\n}\n'''

    def _cli_control_cpp(self) -> str:
        return r'''#include "PapCliControl.h"\n\nnamespace pap\n{\nCliControlBridge::CliControlBridge()\n{\n    auto configured = juce::SystemStats::getEnvironmentVariable("PAP_CONTROL_STATE_FILE", {});\n    if (configured.isNotEmpty())\n        stateFile = juce::File(configured);\n    else\n        stateFile = juce::File::getCurrentWorkingDirectory().getChildFile(".pap/control/runtime_state.json");\n}\n\nvoid CliControlBridge::pollAndApply(juce::AudioProcessorValueTreeState& parameters, juce::MidiBuffer* midi)\n{\n    if (! stateFile.existsAsFile())\n        return;\n\n    const auto modified = stateFile.getLastModificationTime();\n    if (modified == lastStamp)\n        return;\n\n    lastStamp = modified;\n    auto parsed = juce::JSON::parse(stateFile);\n    if (parsed.isVoid() || ! parsed.isObject())\n        return;\n\n    const auto* object = parsed.getDynamicObject();\n    const int eventId = int(object->getProperty("event_id", -1));\n    if (eventId == lastEventId)\n        return;\n    lastEventId = eventId;\n\n    applyParameterObject(object->getProperty("parameters"), parameters);\n    applyMidiArray(object->getProperty("midi"), midi);\n\n    auto transport = object->getProperty("transport");\n    if (transport.isObject())\n    {\n        const bool panic = bool(transport.getProperty("panic", false));\n        if (panic && midi != nullptr)\n        {\n            for (int channel = 1; channel <= 16; ++channel)\n                midi->addEvent(juce::MidiMessage::allNotesOff(channel), 0);\n        }\n    }\n}\n\nvoid CliControlBridge::applyParameterObject(const juce::var& parameterObject, juce::AudioProcessorValueTreeState& parameters)\n{\n    if (! parameterObject.isObject())\n        return;\n\n    const auto& props = parameterObject.getDynamicObject()->getProperties();\n    for (int i = 0; i < props.size(); ++i)\n    {\n        auto key = props.getName(i).toString();\n        auto value = float(props.getValueAt(i));\n        if (auto* parameter = parameters.getParameter(key))\n        {\n            parameter->beginChangeGesture();\n            parameter->setValueNotifyingHost(parameter->convertTo0to1(value));\n            parameter->endChangeGesture();\n        }\n    }\n}\n\nvoid CliControlBridge::applyMidiArray(const juce::var& midiArray, juce::MidiBuffer* midi)\n{\n    if (midi == nullptr || ! midiArray.isArray())\n        return;\n\n    for (const auto& entry : *midiArray.getArray())\n    {\n        if (! entry.isObject())\n            continue;\n\n        const auto type = entry.getProperty("type", "").toString();\n        const int note = int(entry.getProperty("note", 60));\n        const int velocity = int(entry.getProperty("velocity", 100));\n        const int channel = int(entry.getProperty("channel", 1));\n\n        if (type == "on")\n            midi->addEvent(juce::MidiMessage::noteOn(channel, note, (juce::uint8) velocity), 0);\n        else if (type == "off")\n            midi->addEvent(juce::MidiMessage::noteOff(channel, note), 0);\n    }\n}\n}\n'''


def substituted_parameter_layout(text: str) -> str:
    return text
