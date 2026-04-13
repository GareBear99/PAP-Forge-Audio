from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from .contracts import BuildExecutionReceipt, BuildPlan


class BuildPlanner:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.build_root = self.project_root / '.pap' / 'builds'
        self.build_root.mkdir(parents=True, exist_ok=True)

    def create_plan(self, *, checkpoint_id: str, project_name: str, plugin_name: str, template_id: str, target_formats: list[str]) -> BuildPlan:
        build_dir = f'.pap/builds/{checkpoint_id}/execution/cmake_build'
        notes = [
            'Governed PAP build plan.',
            'Uses JUCE_DIR when available or a vendored JUCE checkout if provided later.',
            'Container execution is declared through scripts/pap_build_in_container.py and the juce_builder Docker image.',
        ]
        commands = [
            f'cmake -S . -B {build_dir} -DPAP_CHECKPOINT_ID={checkpoint_id} -DJUCE_DIR=<path>',
            f'cmake --build {build_dir} --config Release',
        ]
        return BuildPlan(
            checkpoint_id=checkpoint_id,
            project_name=project_name,
            plugin_name=plugin_name,
            template_id=template_id,
            container_image='pap/juce-builder:0.9',
            target_formats=target_formats,
            notes=notes,
            builder_mode='local_or_declared',
            environment={'JUCE_DIR': os.environ.get('JUCE_DIR', ''), 'PAP_PROJECT_ROOT': str(self.project_root)},
            output_layout={
                'plan': f'.pap/builds/{checkpoint_id}/build_plan.json',
                'execution': f'.pap/builds/{checkpoint_id}/execution/build_execution.json',
                'cmake_build': build_dir,
                'reproducible_state_current': 'pap/repro_build_state.json',
                'reproducible_state_checkpoint': f'.pap/reproducible_states/{checkpoint_id}.json',
            },
            commands=commands,
        )

    def persist_plan(self, plan: BuildPlan) -> Path:
        target = self.build_root / plan.checkpoint_id / 'build_plan.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding='utf-8')
        return target

    def execute_plan(self, checkpoint_id: str, *, dry_run: bool = True) -> BuildExecutionReceipt:
        output_dir = self.build_root / checkpoint_id / 'execution'
        output_dir.mkdir(parents=True, exist_ok=True)
        commands: list[str] = []
        outputs: list[str] = []
        plan_path = self.build_root / checkpoint_id / 'build_plan.json'
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding='utf-8'))
            commands.extend(plan.get('commands', []))
        if dry_run:
            receipt = BuildExecutionReceipt(status='dry_run', checkpoint_id=checkpoint_id, executed=False, output_dir=str(output_dir.relative_to(self.project_root)), notes=['Dry-run execution receipt only.'], commands=commands, outputs=[])
        else:
            juce_dir = os.environ.get('JUCE_DIR')
            if not juce_dir:
                receipt = BuildExecutionReceipt(status='declared_only', checkpoint_id=checkpoint_id, executed=False, output_dir=str(output_dir.relative_to(self.project_root)), notes=['Execution requested but JUCE_DIR is not set. Plan emitted only.'], commands=commands, outputs=[])
            else:
                build_dir = output_dir / 'cmake_build'
                if build_dir.exists():
                    shutil.rmtree(build_dir)
                build_dir.mkdir(parents=True, exist_ok=True)
                configure = ['cmake', '-S', str(self.project_root), '-B', str(build_dir), f'-DJUCE_DIR={juce_dir}']
                build = ['cmake', '--build', str(build_dir), '--config', 'Release']
                commands = [' '.join(configure), ' '.join(build)]
                notes: list[str] = []
                outputs = []
                status = 'configured'
                try:
                    configured = subprocess.run(configure, capture_output=True, text=True, check=False)
                    (output_dir / 'cmake_configure_stdout.txt').write_text(configured.stdout, encoding='utf-8')
                    (output_dir / 'cmake_configure_stderr.txt').write_text(configured.stderr, encoding='utf-8')
                    outputs.extend([
                        str((output_dir / 'cmake_configure_stdout.txt').relative_to(self.project_root)),
                        str((output_dir / 'cmake_configure_stderr.txt').relative_to(self.project_root)),
                    ])
                    if configured.returncode == 0:
                        built = subprocess.run(build, capture_output=True, text=True, check=False)
                        (output_dir / 'cmake_build_stdout.txt').write_text(built.stdout, encoding='utf-8')
                        (output_dir / 'cmake_build_stderr.txt').write_text(built.stderr, encoding='utf-8')
                        outputs.extend([
                            str((output_dir / 'cmake_build_stdout.txt').relative_to(self.project_root)),
                            str((output_dir / 'cmake_build_stderr.txt').relative_to(self.project_root)),
                        ])
                        status = 'built' if built.returncode == 0 else 'build_failed'
                        notes.append('Concrete build attempted with JUCE_DIR.')
                    else:
                        status = 'configure_failed'
                        notes.append('CMake configure failed. Inspect stderr artifact.')
                except FileNotFoundError:
                    status = 'cmake_missing'
                    notes.append('cmake is not installed in this environment.')
                receipt = BuildExecutionReceipt(status=status, checkpoint_id=checkpoint_id, executed=True, output_dir=str(output_dir.relative_to(self.project_root)), notes=notes, commands=commands, outputs=outputs)
        payload = receipt.to_dict()
        payload['reproducible_state_current'] = 'pap/repro_build_state.json'
        payload['reproducible_state_checkpoint'] = f'.pap/reproducible_states/{checkpoint_id}.json'
        (output_dir / 'build_execution.json').write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
        return receipt
