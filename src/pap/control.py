from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any


class PAPControlSurface:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / '.pap' / 'control'
        self.runtime_state_path = self.root / 'runtime_state.json'
        self.session_path = self.root / 'session.json'
        self.presets_root = self.root / 'presets'
        self.snapshots_root = self.root / 'snapshots'

    def ensure_initialized(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.presets_root.mkdir(parents=True, exist_ok=True)
        self.snapshots_root.mkdir(parents=True, exist_ok=True)
        if not self.session_path.exists():
            self._write_json(self.session_path, {
                'status': 'idle',
                'transport': {'host': '127.0.0.1', 'port': 9031, 'protocol': 'file+osc+udpjson'},
                'checkpoint_id': None,
                'plugin_name': None,
                'state_file': str(self.runtime_state_path.resolve()),
                'bound_at': None,
            })
        if not self.runtime_state_path.exists():
            self._write_json(self.runtime_state_path, self._default_runtime_state())

    def _default_runtime_state(self) -> dict[str, Any]:
        return {
            'schema': 'pap.control.v2',
            'event_id': 0,
            'plugin_name': None,
            'checkpoint_id': None,
            'parameters': {},
            'transport': {
                'panic': False,
                'playing': False,
                'record_armed': False,
                'loop_enabled': False,
                'bpm': 120.0,
                'sample_position': 0,
                'ppq_position': 0.0,
                'bar': 1,
                'beat': 1,
            },
            'midi': [],
            'markers': [],
            'updated_at': time.time(),
        }

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding='utf-8'))

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
        temp.replace(path)

    def bind(self, *, spec, checkpoint_id: str | None, host: str = '127.0.0.1', port: int = 9031) -> dict[str, Any]:
        self.ensure_initialized()
        session = self._read_json(self.session_path)
        session.update({
            'status': 'bound',
            'checkpoint_id': checkpoint_id,
            'plugin_name': spec.plugin_name,
            'plugin_type': spec.plugin_type,
            'state_file': str(self.runtime_state_path.resolve()),
            'bound_at': time.time(),
            'transport': {'host': host, 'port': int(port), 'protocol': 'file+osc+udpjson'},
        })
        self._write_json(self.session_path, session)
        manifest = {
            'schema': 'pap.control_manifest.v2',
            'plugin_name': spec.plugin_name,
            'checkpoint_id': checkpoint_id,
            'plugin_type': spec.plugin_type,
            'state_file': str(self.runtime_state_path.resolve()),
            'osc': {
                'host': host,
                'port': int(port),
                'parameter_prefix': '/pap/param/',
                'note_prefix': '/pap/note/',
                'panic_address': '/pap/panic',
                'transport_address': '/pap/transport',
                'marker_address': '/pap/marker',
            },
            'parameters': spec.parameters,
            'macro_controls': spec.macro_controls,
            'midi_supported': spec.plugin_type == 'synth',
            'transport_supported': True,
            'cli_examples': [
                f'pap control set <project_root> {spec.parameters[0]["id"] if spec.parameters else "output"} 0.75',
                'pap control note <project_root> on 60 100 --channel 1',
                'pap control transport <project_root> --playing true --bpm 128',
            ],
        }
        self._write_json(self.project_root / 'pap' / 'control_manifest.json', manifest)
        state = self._read_json(self.runtime_state_path)
        state.update({'plugin_name': spec.plugin_name, 'checkpoint_id': checkpoint_id, 'updated_at': time.time()})
        self._write_json(self.runtime_state_path, state)
        return manifest

    def status(self) -> dict[str, Any]:
        self.ensure_initialized()
        return {
            'session': self._read_json(self.session_path),
            'runtime_state': self._read_json(self.runtime_state_path),
            'preset_names': sorted(p.stem for p in self.presets_root.glob('*.json')),
            'snapshot_names': sorted(p.stem for p in self.snapshots_root.glob('*.json')),
        }

    def _bump(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload['event_id'] = int(payload.get('event_id', 0)) + 1
        payload['updated_at'] = time.time()
        return payload

    def _session_transport(self) -> tuple[str, int]:
        self.ensure_initialized()
        session = self._read_json(self.session_path)
        transport = session.get('transport', {})
        return str(transport.get('host', '127.0.0.1')), int(transport.get('port', 9031))

    def _send_osc_like(self, address: str, value: Any) -> None:
        host, port = self._session_transport()
        data = json.dumps({'address': address, 'value': value}).encode('utf-8')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(data, (host, port))
        finally:
            sock.close()

    def set_parameter(self, parameter_id: str, value: float, *, send_osc: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        params = dict(state.get('parameters', {}))
        params[parameter_id] = float(value)
        state['parameters'] = params
        self._write_json(self.runtime_state_path, self._bump(state))
        if send_osc:
            self._send_osc_like(f'/pap/param/{parameter_id}', float(value))
        return {'status': 'ok', 'parameter_id': parameter_id, 'value': float(value), 'state_file': str(self.runtime_state_path.resolve())}

    def set_parameters(self, mapping: dict[str, float], *, send_osc: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        params = dict(state.get('parameters', {}))
        for key, value in mapping.items():
            params[str(key)] = float(value)
            if send_osc:
                self._send_osc_like(f'/pap/param/{key}', float(value))
        state['parameters'] = params
        self._write_json(self.runtime_state_path, self._bump(state))
        return {'status': 'ok', 'updated': sorted(mapping.keys()), 'state_file': str(self.runtime_state_path.resolve())}

    def note_event(self, event_type: str, note: int, *, velocity: int = 100, channel: int = 1, send_osc: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        midi = list(state.get('midi', []))
        event = {'type': event_type, 'note': int(note), 'velocity': int(velocity), 'channel': int(channel), 'at': time.time()}
        midi.append(event)
        state['midi'] = midi
        self._write_json(self.runtime_state_path, self._bump(state))
        if send_osc:
            self._send_osc_like(f'/pap/note/{event_type}', event)
        return {'status': 'ok', 'event': event, 'state_file': str(self.runtime_state_path.resolve())}

    def clear_midi(self) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        state['midi'] = []
        self._write_json(self.runtime_state_path, self._bump(state))
        return {'status': 'ok', 'cleared': 'midi'}

    def set_transport(self, *, playing: bool | None = None, record_armed: bool | None = None,
                      loop_enabled: bool | None = None, bpm: float | None = None,
                      sample_position: int | None = None, ppq_position: float | None = None,
                      bar: int | None = None, beat: int | None = None, send_osc: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        transport = dict(state.get('transport', {}))
        updates = {
            'playing': playing,
            'record_armed': record_armed,
            'loop_enabled': loop_enabled,
            'bpm': bpm,
            'sample_position': sample_position,
            'ppq_position': ppq_position,
            'bar': bar,
            'beat': beat,
        }
        applied = {}
        for key, value in updates.items():
            if value is not None:
                transport[key] = value
                applied[key] = value
        state['transport'] = transport
        self._write_json(self.runtime_state_path, self._bump(state))
        if send_osc and applied:
            self._send_osc_like('/pap/transport', applied)
        return {'status': 'ok', 'transport': transport, 'applied': applied}

    def add_marker(self, name: str, *, position_beats: float | None = None, color: str | None = None, send_osc: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        markers = list(state.get('markers', []))
        marker = {'name': name, 'position_beats': position_beats, 'color': color, 'created_at': time.time()}
        markers.append(marker)
        state['markers'] = markers
        self._write_json(self.runtime_state_path, self._bump(state))
        if send_osc:
            self._send_osc_like('/pap/marker', marker)
        return {'status': 'ok', 'marker': marker}

    def panic(self, *, send_osc: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        transport = dict(state.get('transport', {}))
        transport['panic'] = True
        state['transport'] = transport
        state['midi'] = []
        self._write_json(self.runtime_state_path, self._bump(state))
        if send_osc:
            self._send_osc_like('/pap/panic', 1)
        return {'status': 'ok', 'panic': True, 'state_file': str(self.runtime_state_path.resolve())}

    def save_preset(self, name: str) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        payload = {
            'name': name,
            'parameters': state.get('parameters', {}),
            'transport': state.get('transport', {}),
            'saved_at': time.time(),
        }
        target = self.presets_root / f'{name}.json'
        self._write_json(target, payload)
        return {'status': 'ok', 'preset': name, 'path': str(target.relative_to(self.project_root))}

    def load_preset(self, name: str, *, send_osc: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        source = self.presets_root / f'{name}.json'
        payload = self._read_json(source)
        result = self.set_parameters({k: float(v) for k, v in payload.get('parameters', {}).items()}, send_osc=send_osc)
        transport = payload.get('transport', {})
        if isinstance(transport, dict):
            self.set_transport(**{k: transport.get(k) for k in ['playing', 'record_armed', 'loop_enabled', 'bpm', 'sample_position', 'ppq_position', 'bar', 'beat']}, send_osc=send_osc)
        result['preset'] = name
        return result

    def save_snapshot(self, name: str | None = None) -> dict[str, Any]:
        self.ensure_initialized()
        state = self._read_json(self.runtime_state_path)
        timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        snapshot_name = name or f'snapshot_{timestamp}'
        target = self.snapshots_root / f'{snapshot_name}.json'
        payload = {'name': snapshot_name, 'saved_at': time.time(), 'state': state}
        self._write_json(target, payload)
        return {'status': 'ok', 'snapshot': snapshot_name, 'path': str(target.relative_to(self.project_root))}

    def load_snapshot(self, name: str) -> dict[str, Any]:
        self.ensure_initialized()
        source = self.snapshots_root / f'{name}.json'
        payload = self._read_json(source)
        state = payload['state']
        self._write_json(self.runtime_state_path, self._bump(state))
        return {'status': 'ok', 'snapshot': name, 'state_file': str(self.runtime_state_path.resolve())}

    def monitor(self, *, count: int = 1, interval: float = 0.1) -> dict[str, Any]:
        self.ensure_initialized()
        samples = []
        for idx in range(max(1, count)):
            samples.append({'index': idx, 'captured_at': time.time(), 'state': self._read_json(self.runtime_state_path)})
            if idx + 1 < count:
                time.sleep(max(0.0, interval))
        return {'status': 'ok', 'samples': samples}


def run_automation(control: PAPControlSurface, timeline: list[dict[str, Any]], *, speed: float = 1.0, send_osc: bool = False) -> dict[str, Any]:
    control.ensure_initialized()
    started = time.time()
    executed = []
    last_offset = 0.0
    for event in sorted(timeline, key=lambda e: float(e.get('at', 0.0))):
        offset = max(0.0, float(event.get('at', 0.0)))
        wait_s = max(0.0, (offset - last_offset) / max(speed, 1e-6))
        if wait_s > 0.0:
            time.sleep(wait_s)
        kind = str(event.get('kind', 'set'))
        if kind == 'set':
            result = control.set_parameter(str(event['parameter_id']), float(event['value']), send_osc=send_osc)
        elif kind == 'batch':
            result = control.set_parameters({str(k): float(v) for k, v in dict(event.get('values', {})).items()}, send_osc=send_osc)
        elif kind == 'note':
            result = control.note_event(str(event.get('event_type', 'on')), int(event.get('note', 60)), velocity=int(event.get('velocity', 100)), channel=int(event.get('channel', 1)), send_osc=send_osc)
        elif kind == 'panic':
            result = control.panic(send_osc=send_osc)
        elif kind == 'preset-load':
            result = control.load_preset(str(event['name']), send_osc=send_osc)
        elif kind == 'transport':
            result = control.set_transport(
                playing=event.get('playing'),
                record_armed=event.get('record_armed'),
                loop_enabled=event.get('loop_enabled'),
                bpm=float(event['bpm']) if 'bpm' in event else None,
                sample_position=int(event['sample_position']) if 'sample_position' in event else None,
                ppq_position=float(event['ppq_position']) if 'ppq_position' in event else None,
                bar=int(event['bar']) if 'bar' in event else None,
                beat=int(event['beat']) if 'beat' in event else None,
                send_osc=send_osc,
            )
        elif kind == 'marker':
            result = control.add_marker(str(event['name']), position_beats=float(event['position_beats']) if 'position_beats' in event else None, color=event.get('color'), send_osc=send_osc)
        else:
            result = {'status': 'ignored', 'kind': kind}
        executed.append({'at': offset, 'kind': kind, 'result': result})
        last_offset = offset
    return {'status': 'ok', 'started_at': started, 'duration_seconds': time.time() - started, 'events_executed': len(executed), 'events': executed}
