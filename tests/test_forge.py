from pathlib import Path

from pap.project import PAPProject


def template_root() -> Path:
    return Path(__file__).resolve().parents[1] / 'templates' / 'juce_effect_basic'


def test_generate_and_rollback(tmp_path: Path):
    project = PAPProject.init('demo', tmp_path, template_root=template_root())

    first = project.generate_from_prompt('Dark shimmer chorus with macro called Collapse')
    assert first['status'] == 'ok'
    assert (project.root / 'pap' / 'spec.json').exists()
    assert len(project.list_checkpoints()) == 1

    first_cp = first['checkpoint']['checkpoint_id']
    (project.root / 'scratch.txt').write_text('new', encoding='utf-8')

    rolled = project.rollback(first_cp)
    assert rolled['status'] == 'rolled_back'
    assert not (project.root / 'scratch.txt').exists()


def test_spec_writes_plugin_name_and_signal_flow(tmp_path: Path):
    project = PAPProject.init('demo2', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Tape chorus')
    processor_h = (project.root / 'Source' / 'PluginProcessor.h').read_text(encoding='utf-8')
    signal_flow = (project.root / 'pap' / 'signal_flow.txt').read_text(encoding='utf-8')
    assert result['spec']['plugin_name'] in processor_h
    assert 'Input' in signal_flow and 'Output' in signal_flow


def test_branch_and_mutate(tmp_path: Path):
    project = PAPProject.init('demo3', tmp_path, template_root=template_root())
    first = project.generate_from_prompt('Dark chorus')
    first_cp = first['checkpoint']['checkpoint_id']
    created = project.create_branch('crystal', first_cp)
    assert created['status'] == 'created'
    second = project.mutate_from_prompt(first_cp, 'Brighter chorus low cpu', branch_name='crystal')
    assert second['checkpoint']['parent_id'] == first_cp
    assert second['branches']['crystal'] == second['checkpoint']['checkpoint_id']
    assert (project.root / '.pap' / 'builds' / second['checkpoint']['checkpoint_id'] / 'build_plan.json').exists()


def test_synth_prompt_routes_to_synth_template(tmp_path: Path):
    project = PAPProject.init('demo4', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Poly pad synth with analog drift')
    processor_h = (project.root / 'Source' / 'PluginProcessor.h').read_text(encoding='utf-8')
    assert result['spec']['plugin_type'] == 'synth'
    assert result['spec']['template_id'] == 'juce_synth_basic'
    assert 'getPapVoiceMode' in processor_h
    assert 'poly' in processor_h


def test_status_build_and_export(tmp_path: Path):
    project = PAPProject.init('demo5', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Low CPU tape delay')
    checkpoint_id = result['checkpoint']['checkpoint_id']
    status = project.status()
    plan = project.plan_build(checkpoint_id)
    build = project.execute_build(checkpoint_id, dry_run=True)
    export = project.export_bundle()
    assert status['checkpoint_count'] == 1
    assert status['validation']['status'] == 'ok'
    assert plan['checkpoint_id'] == checkpoint_id
    assert build['status'] == 'dry_run'
    assert export['checkpoint_count'] == 1
    assert (project.root / '.pap' / 'graphs' / 'lineage.json').exists()


def test_compare_checkpoints(tmp_path: Path):
    project = PAPProject.init('demo6', tmp_path, template_root=template_root())
    first = project.generate_from_prompt('Dark chorus')
    second = project.mutate_from_prompt(first['checkpoint']['checkpoint_id'], 'Dark chorus with tape drift')
    diff = project.compare(first['checkpoint']['checkpoint_id'], second['checkpoint']['checkpoint_id'])
    assert diff['status'] == 'ok'
    assert 'pap/spec.json' in diff['changed']


def test_validate_warns_before_generation(tmp_path: Path):
    project = PAPProject.init('demo7', tmp_path, template_root=template_root())
    validation = project.validate()
    assert validation['status'] == 'ok'
    assert validation['warnings']


def test_preview_release_and_doctor(tmp_path: Path):
    project = PAPProject.init('demo8', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Poly pad synth with analog drift and shimmer')
    checkpoint_id = result['checkpoint']['checkpoint_id']
    preview_path = project.root / result['receipt']['preview']['wav_path']
    assert preview_path.exists()
    doctor = project.doctor()
    assert doctor['validation']['status'] == 'ok'
    release = project.release(checkpoint_id)
    assert (project.root / release['archive']).exists()
    assert (project.root / '.pap' / 'current.json').exists()
    history = (project.root / '.pap' / 'prompt_history.jsonl').read_text(encoding='utf-8')
    assert checkpoint_id in history


def test_control_manifest_and_runtime_state(tmp_path: Path):
    project = PAPProject.init('demo9', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Poly pad synth with analog drift and shimmer')
    control_manifest = project.root / 'pap' / 'control_manifest.json'
    runtime_state = project.root / '.pap' / 'control' / 'runtime_state.json'
    assert control_manifest.exists()
    assert runtime_state.exists()
    payload = project.control_status()
    assert payload['session']['status'] == 'bound'
    assert payload['runtime_state']['checkpoint_id'] == result['checkpoint']['checkpoint_id']


def test_control_set_note_and_preset(tmp_path: Path):
    project = PAPProject.init('demo10', tmp_path, template_root=template_root())
    project.generate_from_prompt('Poly pad synth with macro collapse')
    project.control_set('mix', 0.77)
    project.control_note('on', 60, velocity=96, channel=2)
    state = project.control_status()['runtime_state']
    assert state['parameters']['mix'] == 0.77
    assert state['midi'][-1]['note'] == 60
    saved = project.control_save_preset('test_patch')
    assert (project.root / saved['path']).exists()
    project.control_set('mix', 0.22)
    project.control_load_preset('test_patch')
    reloaded = project.control_status()['runtime_state']
    assert reloaded['parameters']['mix'] == 0.77


def test_bridge_files_emitted(tmp_path: Path):
    project = PAPProject.init('demo11', tmp_path, template_root=template_root())
    project.generate_from_prompt('Dark shimmer chorus with macro called Collapse')
    assert (project.root / 'pap' / 'bridges' / 'README.md').exists()
    assert (project.root / 'pap' / 'bridges' / 'reaper' / 'PapReaperBridge.py').exists()


def test_reproducible_state_emitted_and_apply_works(tmp_path: Path):
    project = PAPProject.init('demo12', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Dark shimmer chorus with macro called Collapse')
    checkpoint_id = result['checkpoint']['checkpoint_id']
    state_path = project.root / result['reproducible_state']['checkpoint_path']
    assert state_path.exists()
    state = project.reproducible_state_status(checkpoint_id)
    assert state['generated_file_count'] >= 5
    (project.root / 'Source' / 'scratch.txt').write_text('changed', encoding='utf-8')
    applied = project.reproducible_state_apply(checkpoint_id)
    assert applied['status'] == 'applied'
    assert not (project.root / 'Source' / 'scratch.txt').exists()


def test_export_and_release_include_reproducible_state(tmp_path: Path):
    project = PAPProject.init('demo13', tmp_path, template_root=template_root())
    result = project.generate_from_prompt('Poly pad synth with analog drift and shimmer')
    checkpoint_id = result['checkpoint']['checkpoint_id']
    export = project.export_bundle()
    export_manifest = project.root / export['bundle_root'] / 'pap_export_manifest.json'
    assert 'reproducible_states' in export_manifest.read_text(encoding='utf-8')
    release = project.release(checkpoint_id)
    assert release['reproducible_state']['checkpoint_id'] == checkpoint_id
