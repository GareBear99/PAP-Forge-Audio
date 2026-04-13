from pathlib import Path

from pap.project import PAPProject


def template_root() -> Path:
    return Path(__file__).resolve().parents[1] / 'templates' / 'juce_effect_basic'


def test_bootstrap_writes_toolchain_files(tmp_path: Path):
    project = PAPProject.init('demo_bootstrap', tmp_path, template_root=template_root())
    result = project.bootstrap(juce_dir='/tmp/juce', generator='Ninja')
    assert result['status'] == 'ok'
    assert (project.root / '.pap' / 'toolchain' / 'toolchain.json').exists()
    assert (project.root / 'CMakeUserPresets.json').exists()
    assert (project.root / '.pap' / 'scripts' / 'build_local.sh').exists()


def test_report_emits_markdown(tmp_path: Path):
    project = PAPProject.init('demo_report', tmp_path, template_root=template_root())
    project.bootstrap()
    generated = project.generate_from_prompt('Dark shimmer chorus with macro called Collapse')
    payload = project.report()
    report_path = project.root / payload['path']
    text = report_path.read_text(encoding='utf-8')
    assert payload['status'] == 'ok'
    assert generated['checkpoint']['checkpoint_id'] in text
    assert 'Latest build plan' in text
