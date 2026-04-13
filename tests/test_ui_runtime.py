from pathlib import Path

from pap.project import PAPProject


def template_root() -> Path:
    return Path(__file__).resolve().parents[1] / 'templates' / 'juce_effect_basic'


def test_ui_manifest_and_compact_editor_emitted(tmp_path: Path):
    project = PAPProject.init('uidemo', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Dark shimmer chorus with tape drift and macro called Collapse')
    ui_manifest = project.root / 'pap' / 'ui_manifest.json'
    editor_cpp = (project.root / 'Source' / 'PluginEditor.cpp').read_text(encoding='utf-8')
    ui_runtime = (project.root / 'Source' / 'PapUiRuntime.h').read_text(encoding='utf-8')
    assert ui_manifest.exists()
    assert 'compact_runtime' in ui_manifest.read_text(encoding='utf-8')
    assert 'Primary Controls' in editor_cpp
    assert 'CLI Bridge: Live' in editor_cpp
    assert 'compact_runtime' in ui_runtime
    status = project.ui_status()
    assert status['status'] == 'ok'
    assert status['ui']['plugin_name'] == result['spec']['plugin_name']
