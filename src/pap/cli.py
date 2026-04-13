from __future__ import annotations

import json
import sys
from pathlib import Path

from .project import PAPProject


def _template_root() -> Path:
    return Path(__file__).resolve().parents[2] / 'templates' / 'juce_effect_basic'


def _bool_arg(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {'1', 'true', 'yes', 'on'}:
        return True
    if lowered in {'0', 'false', 'no', 'off'}:
        return False
    raise ValueError(f'Invalid boolean value: {value}')


def _print(payload) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def _require_len(argv: list[str], n: int, usage: str) -> None:
    if len(argv) < n:
        raise SystemExit(usage)


def _load_project(project_root: str) -> PAPProject:
    return PAPProject.open(project_root)


def _cmd_control(argv: list[str]) -> int:
    _require_len(argv, 3, 'usage: control <status|bind|set|batch|note|panic|preset-save|preset-load|automation|serve|export-shell|transport|marker|snapshot-save|snapshot-load|monitor|clear-midi> <project_root> ...')
    sub = argv[1]
    project = _load_project(argv[2])

    if sub == 'status':
        return _print(project.control_status())

    if sub == 'bind':
        checkpoint_id = None
        host = '127.0.0.1'
        port = 9031
        rest = argv[3:]
        if rest and not rest[0].startswith('--'):
            checkpoint_id = rest[0]
            rest = rest[1:]
        if '--host' in rest:
            idx = rest.index('--host')
            host = rest[idx + 1]
        if '--port' in rest:
            idx = rest.index('--port')
            port = int(rest[idx + 1])
        return _print(project.control_bind(checkpoint_id, host=host, port=port))

    if sub == 'set':
        _require_len(argv, 5, 'usage: control set <project_root> <parameter_id> <value> [--osc]')
        return _print(project.control_set(argv[3], float(argv[4]), send_osc='--osc' in argv[5:]))

    if sub == 'batch':
        _require_len(argv, 4, 'usage: control batch <project_root> <json_path> [--osc]')
        payload = json.loads(Path(argv[3]).read_text(encoding='utf-8'))
        return _print(project.control_batch(payload, send_osc='--osc' in argv[4:]))

    if sub == 'note':
        _require_len(argv, 6, 'usage: control note <project_root> <on|off> <note> <velocity> [--channel N] [--osc]')
        rest = argv[6:]
        channel = 1
        if '--channel' in rest:
            idx = rest.index('--channel')
            channel = int(rest[idx + 1])
        return _print(project.control_note(argv[3], int(argv[4]), velocity=int(argv[5]), channel=channel, send_osc='--osc' in rest))

    if sub == 'panic':
        return _print(project.control_panic(send_osc='--osc' in argv[3:]))

    if sub == 'preset-save':
        _require_len(argv, 4, 'usage: control preset-save <project_root> <name>')
        return _print(project.control_save_preset(argv[3]))

    if sub == 'preset-load':
        _require_len(argv, 4, 'usage: control preset-load <project_root> <name> [--osc]')
        return _print(project.control_load_preset(argv[3], send_osc='--osc' in argv[4:]))

    if sub == 'automation':
        _require_len(argv, 4, 'usage: control automation <project_root> <timeline.json> [--speed N] [--osc]')
        timeline = json.loads(Path(argv[3]).read_text(encoding='utf-8'))
        speed = 1.0
        rest = argv[4:]
        if '--speed' in rest:
            idx = rest.index('--speed')
            speed = float(rest[idx + 1])
        return _print(project.control_automation(timeline, speed=speed, send_osc='--osc' in rest))

    if sub == 'serve':
        from .control_daemon import PAPControlDaemon
        host = '127.0.0.1'
        port = 9031
        timeout_seconds = None
        rest = argv[3:]
        if '--host' in rest:
            idx = rest.index('--host')
            host = rest[idx + 1]
        if '--port' in rest:
            idx = rest.index('--port')
            port = int(rest[idx + 1])
        if '--timeout' in rest:
            idx = rest.index('--timeout')
            timeout_seconds = float(rest[idx + 1])
        daemon = PAPControlDaemon(project.root, host=host, port=port)
        return _print(daemon.serve_forever(timeout_seconds=timeout_seconds))

    if sub == 'export-shell':
        return _print(project.control_export_shell())

    if sub == 'transport':
        rest = argv[3:]
        kwargs = {}
        for key in ['playing', 'record-armed', 'loop-enabled']:
            flag = f'--{key}'
            if flag in rest:
                idx = rest.index(flag)
                kwargs[key.replace('-', '_')] = _bool_arg(rest[idx + 1])
        numeric = {'bpm': float, 'sample-position': int, 'ppq-position': float, 'bar': int, 'beat': int}
        for key, caster in numeric.items():
            flag = f'--{key}'
            if flag in rest:
                idx = rest.index(flag)
                kwargs[key.replace('-', '_')] = caster(rest[idx + 1])
        kwargs['send_osc'] = '--osc' in rest
        return _print(project.control_transport(**kwargs))

    if sub == 'marker':
        _require_len(argv, 4, 'usage: control marker <project_root> <name> [--position-beats N] [--color COLOR] [--osc]')
        rest = argv[4:]
        position_beats = None
        color = None
        if '--position-beats' in rest:
            idx = rest.index('--position-beats')
            position_beats = float(rest[idx + 1])
        if '--color' in rest:
            idx = rest.index('--color')
            color = rest[idx + 1]
        return _print(project.control_marker(argv[3], position_beats=position_beats, color=color, send_osc='--osc' in rest))

    if sub == 'snapshot-save':
        name = argv[3] if len(argv) > 3 else None
        return _print(project.control_save_snapshot(name))

    if sub == 'snapshot-load':
        _require_len(argv, 4, 'usage: control snapshot-load <project_root> <name>')
        return _print(project.control_load_snapshot(argv[3]))

    if sub == 'monitor':
        rest = argv[3:]
        count = 1
        interval = 0.1
        if '--count' in rest:
            idx = rest.index('--count')
            count = int(rest[idx + 1])
        if '--interval' in rest:
            idx = rest.index('--interval')
            interval = float(rest[idx + 1])
        return _print(project.control_monitor(count=count, interval=interval))

    if sub == 'clear-midi':
        return _print(project.control_clear_midi())

    raise SystemExit(f'unknown control command: {sub}')


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print('usage: pap <init|bootstrap|generate|mutate|spec|status|ui|validate|doctor|report|plan|build|export|release|checkpoints|branches|branch|compare|rollback|state|state-apply|state-list|control> ...')
        return 1

    cmd = argv[0]
    if cmd == 'init':
        _require_len(argv, 3, 'usage: init <project_name> <workspace_root>')
        project = PAPProject.init(argv[1], argv[2], template_root=_template_root())
        return _print({'status': 'ok', 'project_root': str(project.root)})
    if cmd == 'bootstrap':
        _require_len(argv, 2, 'usage: bootstrap <project_root> [--juce-dir PATH] [--generator NAME]')
        project = _load_project(argv[1])
        juce_dir = None
        generator = 'Ninja'
        if '--juce-dir' in argv[2:]:
            idx = argv.index('--juce-dir')
            juce_dir = argv[idx + 1]
        if '--generator' in argv[2:]:
            idx = argv.index('--generator')
            generator = argv[idx + 1]
        return _print(project.bootstrap(juce_dir=juce_dir, generator=generator))
    if cmd == 'generate':
        _require_len(argv, 3, 'usage: generate <project_root> <prompt> [--branch NAME]')
        project = _load_project(argv[1])
        branch_name = 'main'
        args = argv[2:]
        if '--branch' in args:
            idx = args.index('--branch')
            branch_name = args[idx + 1]
            del args[idx:idx + 2]
        return _print(project.generate_from_prompt(' '.join(args), branch_name=branch_name))
    if cmd == 'mutate':
        _require_len(argv, 4, 'usage: mutate <project_root> <checkpoint_id> <prompt> [--branch NAME]')
        project = _load_project(argv[1])
        checkpoint_id = argv[2]
        branch_name = 'main'
        args = argv[3:]
        if '--branch' in args:
            idx = args.index('--branch')
            branch_name = args[idx + 1]
            del args[idx:idx + 2]
        return _print(project.mutate_from_prompt(checkpoint_id, ' '.join(args), branch_name=branch_name))
    if cmd == 'spec':
        _require_len(argv, 3, 'usage: spec <project_root> <prompt>')
        return _print(_load_project(argv[1]).spec_from_prompt(' '.join(argv[2:])))
    if cmd == 'status':
        return _print(_load_project(argv[1]).status())
    if cmd == 'ui':
        return _print(_load_project(argv[1]).ui_status())
    if cmd == 'validate':
        return _print(_load_project(argv[1]).validate())
    if cmd == 'doctor':
        return _print(_load_project(argv[1]).doctor())
    if cmd == 'report':
        return _print(_load_project(argv[1]).report())
    if cmd == 'plan':
        _require_len(argv, 3, 'usage: plan <project_root> <checkpoint_id>')
        return _print(_load_project(argv[1]).plan_build(argv[2]))
    if cmd == 'build':
        _require_len(argv, 3, 'usage: build <project_root> <checkpoint_id> [--execute]')
        return _print(_load_project(argv[1]).execute_build(argv[2], dry_run='--execute' not in argv[3:]))
    if cmd == 'export':
        return _print(_load_project(argv[1]).export_bundle())
    if cmd == 'release':
        project = _load_project(argv[1])
        checkpoint_id = argv[2] if len(argv) > 2 else None
        return _print(project.release(checkpoint_id))
    if cmd == 'checkpoints':
        return _print(_load_project(argv[1]).list_checkpoints())
    if cmd == 'branches':
        return _print(_load_project(argv[1]).list_branches())
    if cmd == 'branch':
        _require_len(argv, 3, 'usage: branch <project_root> <branch_name> [from_checkpoint_id]')
        from_cp = argv[3] if len(argv) > 3 else None
        return _print(_load_project(argv[1]).create_branch(argv[2], from_cp))
    if cmd == 'compare':
        _require_len(argv, 4, 'usage: compare <project_root> <left_checkpoint_id> <right_checkpoint_id>')
        return _print(_load_project(argv[1]).compare(argv[2], argv[3]))
    if cmd == 'rollback':
        _require_len(argv, 3, 'usage: rollback <project_root> <checkpoint_id>')
        return _print(_load_project(argv[1]).rollback(argv[2]))
    if cmd == 'state':
        _require_len(argv, 2, 'usage: state <project_root> [checkpoint_id|state_json_path]')
        state_ref = argv[2] if len(argv) > 2 else None
        return _print(_load_project(argv[1]).reproducible_state_status(state_ref))
    if cmd == 'state-apply':
        _require_len(argv, 3, 'usage: state-apply <project_root> <checkpoint_id|state_json_path>')
        return _print(_load_project(argv[1]).reproducible_state_apply(argv[2]))
    if cmd == 'state-list':
        _require_len(argv, 2, 'usage: state-list <project_root>')
        return _print(_load_project(argv[1]).reproducible_state_list())
    if cmd == 'control':
        return _cmd_control(argv)

    print(f'unknown command: {cmd}')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
