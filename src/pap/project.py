from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from .artifacts import ArtifactStore
from .bootstrap import bootstrap_project
from .branches import BranchStore
from .builds import BuildPlanner
from .compare import CheckpointComparator
from .control import PAPControlSurface, run_automation
from .checkpoints import CheckpointStore
from .contracts import BuildReceipt, GenerationRequest, MutationRequest
from .graph import LineageGraph
from .manifests import project_status_manifest, write_json
from .preview import PreviewRenderer
from .reproducible import ReproducibleStateStore
from .specs import spec_from_prompt
from .templates import TemplateLibrary
from .validators import ProjectValidator


class PAPProject:
    def __init__(self, root: str | Path, *, template_root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.template_root = Path(template_root)
        self.checkpoints = CheckpointStore(self.root)
        self.templates = TemplateLibrary(self.template_root)
        self.config_path = self.root / '.pap' / 'project.json'
        self.branches = BranchStore(self.root)
        self.artifacts = ArtifactStore(self.root)
        self.builds = BuildPlanner(self.root)
        self.graph = LineageGraph(self.root)
        self.validator = ProjectValidator(self.root)
        self.comparator = CheckpointComparator(self.root)
        self.preview = PreviewRenderer(self.root)
        self.control = PAPControlSurface(self.root)
        self.reproducible = ReproducibleStateStore(self.root)
        self.prompt_history_path = self.root / '.pap' / 'prompt_history.jsonl'
        self.current_path = self.root / '.pap' / 'current.json'

    @classmethod
    def init(cls, project_name: str, workspace_root: str | Path, *, template_root: str | Path) -> 'PAPProject':
        project_root = Path(workspace_root) / project_name
        project = cls(project_root, template_root=template_root)
        config = {
            'project_name': project_name,
            'template_root': str(Path(template_root).resolve()),
            'category': 'PAP',
            'default_branch': 'main',
            'repo_version': '1.5.0',
            'policies': {
                'realtime_safe_generation': False,
                'container_build_declared': True,
                'checkpointed_mutation': True,
                'offline_preview_rendering': True,
                'cli_daw_control': True,
                'transport_bridge': True,
                'runtime_snapshots': True,
                'json_reproducible_build_state': True,
            },
        }
        project.config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding='utf-8')
        if not project.prompt_history_path.exists():
            project.prompt_history_path.write_text('', encoding='utf-8')
        write_json(project.current_path, {'branch': 'main', 'checkpoint_id': None})
        project.control.ensure_initialized()
        return project

    @classmethod
    def open(cls, root: str | Path) -> 'PAPProject':
        root = Path(root)
        config_path = root / '.pap' / 'project.json'
        if not config_path.exists():
            raise FileNotFoundError(f'Missing PAP config: {config_path}')
        config = json.loads(config_path.read_text(encoding='utf-8'))
        return cls(root, template_root=config['template_root'])

    @property
    def project_name(self) -> str:
        return json.loads(self.config_path.read_text(encoding='utf-8'))['project_name']

    def generate_from_prompt(self, prompt: str, *, branch_name: str = 'main') -> dict[str, object]:
        return self._generate(GenerationRequest(prompt=prompt, preferred_branch=branch_name))

    def mutate_from_prompt(self, checkpoint_id: str, prompt: str, *, branch_name: str = 'main') -> dict[str, object]:
        _ = MutationRequest(checkpoint_id=checkpoint_id, prompt=prompt, target_branch=branch_name)
        return self._generate(GenerationRequest(prompt=prompt, preferred_branch=branch_name), explicit_parent=checkpoint_id)

    def spec_from_prompt(self, prompt: str) -> dict[str, object]:
        return spec_from_prompt(prompt).to_dict()

    def _generate(self, request: GenerationRequest, explicit_parent: str | None = None) -> dict[str, object]:
        spec = spec_from_prompt(request.prompt)
        rendered = self.templates.render(spec)
        rendered.files.update(self._compact_ui_runtime_files(spec))
        self._write_rendered(rendered.files)

        parent_id = explicit_parent if explicit_parent is not None else self.branches.head(request.preferred_branch)
        manifest = self.checkpoints.save_checkpoint(prompt=request.prompt, plugin_name=spec.plugin_name, template_id=rendered.template_id, parent_id=parent_id)
        self.branches.update_head(manifest.checkpoint_id, request.preferred_branch)
        self._append_prompt_history(branch=request.preferred_branch, prompt=request.prompt, checkpoint_id=manifest.checkpoint_id)

        artifacts = [self.artifacts.record_text(manifest.checkpoint_id, rel_path, content) for rel_path, content in sorted(rendered.files.items())]
        preview = self.preview.render(manifest.checkpoint_id, spec)
        artifacts.append(self.artifacts.snapshot_file(manifest.checkpoint_id, self.root / preview.wav_path, kind='preview_wav'))
        control_manifest = self.control.bind(spec=spec, checkpoint_id=manifest.checkpoint_id)
        artifacts.append(self.artifacts.snapshot_file(manifest.checkpoint_id, self.root / 'pap' / 'control_manifest.json', kind='control_manifest'))
        build_plan = self.builds.create_plan(checkpoint_id=manifest.checkpoint_id, project_name=self.project_name, plugin_name=spec.plugin_name, template_id=rendered.template_id, target_formats=spec.target_formats)
        self.builds.persist_plan(build_plan)
        self._emit_status_files(current_branch=request.preferred_branch, current_checkpoint=manifest.checkpoint_id)

        receipt = BuildReceipt(
            status='ok',
            checkpoint_id=manifest.checkpoint_id,
            plugin_name=spec.plugin_name,
            template_id=rendered.template_id,
            written_files=sorted(rendered.files.keys()),
            notes=[
                'Scaffold generated successfully.',
                'Offline preview render was emitted under .pap/previews/.',
                'Concrete plugin compilation still depends on a JUCE + compiler toolchain.',
                'Canonical JSON reproducible build state was emitted for this checkpoint.',
            ],
            artifacts=artifacts,
            build_plan=build_plan,
            preview=preview.to_dict(),
        )
        reproducible_state = self.reproducible.save_state(
            checkpoint=manifest.to_dict(),
            request=request.to_dict(),
            spec=spec.to_dict(),
            rendered_files=rendered.files,
            branches=self.branches.list_branches(),
            current_branch=request.preferred_branch,
            build_plan=build_plan.to_dict(),
            receipt=receipt.to_dict(),
            preview=preview.to_dict(),
            control_manifest=control_manifest,
        )
        return {
            'status': 'ok',
            'request': request.to_dict(),
            'spec': spec.to_dict(),
            'checkpoint': manifest.to_dict(),
            'receipt': receipt.to_dict(),
            'reproducible_state': reproducible_state,
            'written_files': receipt.written_files,
            'branches': self.branches.list_branches(),
        }


    def _compact_ui_runtime_files(self, spec) -> dict[str, str]:
        primary_ids = [p['id'] for p in spec.parameters[:6]]
        return {
            'pap/ui_manifest.json': json.dumps({
                'schema': 'pap.ui_manifest.v1',
                'plugin_name': spec.plugin_name,
                'plugin_type': spec.plugin_type,
                'layout': 'compact_runtime',
                'sections': ['main_controls', 'runtime', 'signal_flow'],
                'primary_controls': primary_ids,
                'macro_controls': spec.macro_controls,
                'signal_flow': spec.signal_flow,
                'control_bridge': {
                    'enabled': True,
                    'state_file': '.pap/control/runtime_state.json',
                    'transport_supported': True,
                },
            }, indent=2) + '\n',
            'Source/PapUiRuntime.h': '\n'.join([
                '#pragma once',
                '',
                'namespace pap',
                '{',
                'inline const char* getPapUiLayoutName() noexcept { return "compact_runtime"; }',
                f'inline const char* getPapUiPluginType() noexcept {{ return "{spec.plugin_type}"; }}',
                'inline const char* getPapUiCheckpointHint() noexcept { return "Generated from PAP checkpoint state"; }',
                'inline const char* getPapUiRuntimeSummary() noexcept { return "Compact controls + runtime status + signal flow"; }',
                'inline const char* getPapUiPrimaryControlIds() noexcept { return "' + ', '.join(primary_ids) + '"; }',
                '}',
                ''
            ]),
        }

    def _write_rendered(self, files: dict[str, str]) -> None:
        for rel, content in files.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')

    def _append_prompt_history(self, *, branch: str, prompt: str, checkpoint_id: str) -> None:
        with self.prompt_history_path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps({'branch': branch, 'prompt': prompt, 'checkpoint_id': checkpoint_id}) + '\n')

    def _emit_status_files(self, *, current_branch: str | None = None, current_checkpoint: str | None = None) -> None:
        checkpoints = self.list_checkpoints()
        branches = self.list_branches()
        validation = self.validator.validate()
        write_json(self.root / '.pap' / 'status.json', project_status_manifest(project_name=self.project_name, branches=branches, checkpoints=checkpoints, validation=validation))
        self.graph.emit(checkpoints, branches)
        if current_branch is None:
            current_branch = next((k for k, v in branches.items() if v == (checkpoints[-1]['checkpoint_id'] if checkpoints else None)), 'main')
        write_json(self.current_path, {'branch': current_branch, 'checkpoint_id': current_checkpoint or (checkpoints[-1]['checkpoint_id'] if checkpoints else None)})

    def list_checkpoints(self) -> list[dict[str, object]]:
        return self.checkpoints.list_checkpoints()

    def list_branches(self) -> dict[str, str | None]:
        return self.branches.list_branches()

    def create_branch(self, branch_name: str, from_checkpoint_id: str | None = None) -> dict[str, object]:
        if from_checkpoint_id is None:
            from_checkpoint_id = self.branches.head('main')
        payload = self.branches.create_branch(branch_name, from_checkpoint_id)
        self._emit_status_files(current_branch=branch_name, current_checkpoint=from_checkpoint_id)
        return payload

    def rollback(self, checkpoint_id: str) -> dict[str, object]:
        payload = self.checkpoints.rollback(checkpoint_id)
        self._emit_status_files(current_checkpoint=checkpoint_id)
        return payload

    def status(self) -> dict[str, object]:
        self._emit_status_files()
        return project_status_manifest(project_name=self.project_name, branches=self.list_branches(), checkpoints=self.list_checkpoints(), validation=self.validator.validate())

    def validate(self) -> dict[str, object]:
        return self.validator.validate()

    def ui_status(self) -> dict[str, object]:
        manifest_path = self.root / 'pap' / 'ui_manifest.json'
        if not manifest_path.exists():
            return {'status': 'missing', 'message': 'Generate a plugin first to emit the compact UI manifest.'}
        payload = json.loads(manifest_path.read_text(encoding='utf-8'))
        return {'status': 'ok', 'ui': payload}

    def plan_build(self, checkpoint_id: str) -> dict[str, object]:
        plan_path = self.root / '.pap' / 'builds' / checkpoint_id / 'build_plan.json'
        return json.loads(plan_path.read_text(encoding='utf-8'))

    def execute_build(self, checkpoint_id: str, *, dry_run: bool = True) -> dict[str, object]:
        return self.builds.execute_plan(checkpoint_id, dry_run=dry_run).to_dict()

    def compare(self, left_checkpoint_id: str, right_checkpoint_id: str) -> dict[str, object]:
        return self.comparator.compare(left_checkpoint_id, right_checkpoint_id)

    def reproducible_state_status(self, checkpoint_id: str | None = None) -> dict[str, object]:
        state = self.reproducible.load_state(checkpoint_id)
        return {
            'status': 'ok',
            'schema': state.get('schema'),
            'checkpoint_id': state.get('checkpoint', {}).get('checkpoint_id'),
            'plugin_name': state.get('spec', {}).get('plugin_name'),
            'generated_file_count': len(state.get('generated_files', {})),
            'paths': state.get('state_paths', {}),
        }

    def reproducible_state_apply(self, path_or_checkpoint: str | None = None) -> dict[str, object]:
        payload = self.reproducible.apply_state(path_or_checkpoint)
        self._emit_status_files(current_checkpoint=payload.get('checkpoint_id'))
        return payload

    def reproducible_state_list(self) -> dict[str, object]:
        return {'status': 'ok', 'states': self.reproducible.list_states()}

    def export_bundle(self) -> dict[str, object]:
        export_root = self.root / '.pap' / 'exports'
        export_root.mkdir(parents=True, exist_ok=True)
        bundle_path = export_root / f'{self.project_name}_bundle'
        if bundle_path.exists():
            shutil.rmtree(bundle_path)
        bundle_path.mkdir(parents=True, exist_ok=True)
        for child in self.root.iterdir():
            if child.name == '.pap':
                continue
            target = bundle_path / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)
        write_json(bundle_path / 'pap_export_manifest.json', {
            'project_name': self.project_name,
            'bundle_root': str(bundle_path.relative_to(self.root)),
            'branches': self.list_branches(),
            'checkpoint_count': len(self.list_checkpoints()),
            'reproducible_states': self.reproducible.list_states(),
        })
        return {'project_name': self.project_name, 'bundle_root': str(bundle_path.relative_to(self.root)), 'checkpoint_count': len(self.list_checkpoints())}

    def release(self, checkpoint_id: str | None = None) -> dict[str, object]:
        checkpoints = self.list_checkpoints()
        if checkpoint_id is None:
            if not checkpoints:
                raise ValueError('No checkpoints available for release.')
            checkpoint_id = checkpoints[-1]['checkpoint_id']
        release_root = self.root / '.pap' / 'releases' / checkpoint_id
        if release_root.exists():
            shutil.rmtree(release_root)
        release_root.mkdir(parents=True, exist_ok=True)
        snapshot = self.root / '.pap' / 'snapshots' / checkpoint_id
        if snapshot.exists():
            shutil.copytree(snapshot, release_root / 'project', dirs_exist_ok=True)
        preview_dir = self.root / '.pap' / 'previews' / checkpoint_id
        if preview_dir.exists():
            shutil.copytree(preview_dir, release_root / 'preview', dirs_exist_ok=True)
        manifest = {
            'project_name': self.project_name,
            'checkpoint_id': checkpoint_id,
            'branches': self.list_branches(),
            'validation': self.validate(),
            'reproducible_state': self.reproducible_state_status(checkpoint_id),
        }
        write_json(release_root / 'release_manifest.json', manifest)
        archive = self.root / '.pap' / 'releases' / f'{self.project_name}_{checkpoint_id}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in release_root.rglob('*'):
                if path.is_file():
                    zf.write(path, path.relative_to(release_root.parent))
        manifest['archive'] = str(archive.relative_to(self.root))
        return manifest


    def control_status(self) -> dict[str, object]:
        return self.control.status()

    def control_bind(self, checkpoint_id: str | None = None, host: str = '127.0.0.1', port: int = 9031) -> dict[str, object]:
        checkpoints = self.list_checkpoints()
        if checkpoint_id is None and checkpoints:
            checkpoint_id = checkpoints[-1]['checkpoint_id']
        spec_path = self.root / 'pap' / 'spec.json'
        if not spec_path.exists():
            raise ValueError('No generated spec exists yet; generate a plugin first.')
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        from .specs import PluginSpec
        return self.control.bind(spec=PluginSpec(**spec), checkpoint_id=checkpoint_id, host=host, port=port)

    def control_set(self, parameter_id: str, value: float, *, send_osc: bool = False) -> dict[str, object]:
        return self.control.set_parameter(parameter_id, value, send_osc=send_osc)

    def control_batch(self, mapping: dict[str, float], *, send_osc: bool = False) -> dict[str, object]:
        return self.control.set_parameters(mapping, send_osc=send_osc)

    def control_note(self, event_type: str, note: int, velocity: int = 100, channel: int = 1, *, send_osc: bool = False) -> dict[str, object]:
        return self.control.note_event(event_type, note, velocity=velocity, channel=channel, send_osc=send_osc)

    def control_panic(self, *, send_osc: bool = False) -> dict[str, object]:
        return self.control.panic(send_osc=send_osc)

    def control_save_preset(self, name: str) -> dict[str, object]:
        return self.control.save_preset(name)

    def control_load_preset(self, name: str, *, send_osc: bool = False) -> dict[str, object]:
        return self.control.load_preset(name, send_osc=send_osc)


    def control_automation(self, timeline: list[dict[str, object]], *, speed: float = 1.0, send_osc: bool = False) -> dict[str, object]:
        return run_automation(self.control, timeline, speed=speed, send_osc=send_osc)


    def control_transport(self, **kwargs) -> dict[str, object]:
        return self.control.set_transport(**kwargs)

    def control_marker(self, name: str, *, position_beats: float | None = None, color: str | None = None, send_osc: bool = False) -> dict[str, object]:
        return self.control.add_marker(name, position_beats=position_beats, color=color, send_osc=send_osc)

    def control_save_snapshot(self, name: str | None = None) -> dict[str, object]:
        return self.control.save_snapshot(name)

    def control_load_snapshot(self, name: str) -> dict[str, object]:
        return self.control.load_snapshot(name)

    def control_monitor(self, *, count: int = 1, interval: float = 0.1) -> dict[str, object]:
        return self.control.monitor(count=count, interval=interval)

    def control_clear_midi(self) -> dict[str, object]:
        return self.control.clear_midi()

    def control_export_shell(self) -> dict[str, object]:
        self.control.ensure_initialized()
        target = self.root / '.pap' / 'control' / 'pap_control_env.sh'
        state_file = self.root / '.pap' / 'control' / 'runtime_state.json'
        target.write_text('\n'.join([
            '#!/usr/bin/env bash',
            '# Auto-generated by PAP Forge',
            f'export PAP_PROJECT_ROOT="{self.root.resolve()}"',
            f'export PAP_CONTROL_STATE_FILE="{state_file.resolve()}"',
            'echo "PAP control env ready"',
            'echo "PAP_CONTROL_STATE_FILE=$PAP_CONTROL_STATE_FILE"',
        ]) + '\n', encoding='utf-8')
        target.chmod(0o755)
        return {'status': 'ok', 'path': str(target.relative_to(self.root))}


    def bootstrap(self, *, juce_dir: str | None = None, generator: str = 'Ninja') -> dict[str, object]:
        return bootstrap_project(self.root, juce_dir=juce_dir, generator=generator)

    def report(self) -> dict[str, object]:
        status = self.status()
        doctor = self.doctor()
        current = json.loads(self.current_path.read_text(encoding='utf-8')) if self.current_path.exists() else {'branch': None, 'checkpoint_id': None}
        latest_checkpoint = current.get('checkpoint_id')
        latest_plan = None
        if latest_checkpoint:
            plan_path = self.root / '.pap' / 'builds' / latest_checkpoint / 'build_plan.json'
            if plan_path.exists():
                latest_plan = json.loads(plan_path.read_text(encoding='utf-8'))
        report_lines = [
            f'# PAP Report — {self.project_name}',
            '',
            f"- Current branch: `{current.get('branch')}`",
            f"- Current checkpoint: `{current.get('checkpoint_id')}`",
            f"- Checkpoints: `{status['checkpoint_count']}`",
            f"- Validation: `{status['validation']['status']}`",
            '',
            '## Tool visibility',
        ]
        for name, meta in doctor['tools'].items():
            report_lines.append(f"- {name}: {'found' if meta['found'] else 'missing'} {meta.get('headline','').strip()}")
        if latest_plan:
            report_lines.extend(['', '## Latest build plan', f"- Container image: `{latest_plan.get('container_image','')}`"])
            for cmd in latest_plan.get('commands', []):
                report_lines.append(f"- `{cmd}`")
        target = self.root / '.pap' / 'reports' / 'project_report.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')
        return {'status': 'ok', 'path': str(target.relative_to(self.root)), 'current': current, 'validation': status['validation']}

    def doctor(self) -> dict[str, object]:
        tools = {}
        for exe in ['python', 'cmake', 'ninja', 'docker']:
            try:
                result = subprocess.run([exe, '--version'], capture_output=True, text=True, check=False)
                tools[exe] = {'found': True, 'code': result.returncode, 'headline': (result.stdout or result.stderr).splitlines()[0] if (result.stdout or result.stderr) else ''}
            except FileNotFoundError:
                tools[exe] = {'found': False, 'code': None, 'headline': ''}
        payload = {
            'project_name': self.project_name,
            'validation': self.validate(),
            'tools': tools,
            'juce_dir_set': bool(__import__('os').environ.get('JUCE_DIR')),
            'juce_dir_exists': bool(__import__('os').environ.get('JUCE_DIR') and Path(__import__('os').environ.get('JUCE_DIR')).exists()),
        }
        write_json(self.root / '.pap' / 'doctor.json', payload)
        return payload
