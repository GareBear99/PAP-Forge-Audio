from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any

from .control import PAPControlSurface


class PAPControlDaemon:
    def __init__(self, project_root: str | Path, *, host: str = '127.0.0.1', port: int = 9031) -> None:
        self.project_root = Path(project_root)
        self.control = PAPControlSurface(self.project_root)
        self.host = host
        self.port = int(port)
        self.running = False
        self.socket: socket.socket | None = None

    def _write_daemon_status(self, status: str, extra: dict[str, Any] | None = None) -> None:
        self.control.ensure_initialized()
        payload = self.control._read_json(self.control.session_path)
        payload['daemon'] = {
            'status': status,
            'host': self.host,
            'port': self.port,
            'updated_at': time.time(),
        }
        if extra:
            payload['daemon'].update(extra)
        self.control._write_json(self.control.session_path, payload)

    def _handle_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        address = str(payload.get('address', ''))
        value = payload.get('value')
        if address.startswith('/pap/param/'):
            parameter_id = address.split('/pap/param/', 1)[1]
            return self.control.set_parameter(parameter_id, float(value), send_osc=False)
        if address == '/pap/params' and isinstance(value, dict):
            return self.control.set_parameters({str(k): float(v) for k, v in value.items()}, send_osc=False)
        if address in ('/pap/note/on', '/pap/note/off') and isinstance(value, dict):
            event_type = 'on' if address.endswith('/on') else 'off'
            return self.control.note_event(
                event_type,
                int(value.get('note', 60)),
                velocity=int(value.get('velocity', 100)),
                channel=int(value.get('channel', 1)),
                send_osc=False,
            )
        if address == '/pap/panic':
            return self.control.panic(send_osc=False)
        if address == '/pap/preset/load':
            return self.control.load_preset(str(value), send_osc=False)
        if address == '/pap/preset/save':
            return self.control.save_preset(str(value))
        if address == '/pap/transport' and isinstance(value, dict):
            return self.control.set_transport(
                playing=value.get('playing'),
                record_armed=value.get('record_armed'),
                loop_enabled=value.get('loop_enabled'),
                bpm=float(value['bpm']) if 'bpm' in value else None,
                sample_position=int(value['sample_position']) if 'sample_position' in value else None,
                ppq_position=float(value['ppq_position']) if 'ppq_position' in value else None,
                bar=int(value['bar']) if 'bar' in value else None,
                beat=int(value['beat']) if 'beat' in value else None,
                send_osc=False,
            )
        if address == '/pap/marker' and isinstance(value, dict):
            return self.control.add_marker(
                str(value.get('name', 'marker')),
                position_beats=float(value['position_beats']) if 'position_beats' in value and value['position_beats'] is not None else None,
                color=value.get('color'),
                send_osc=False,
            )
        if address == '/pap/midi/clear':
            return self.control.clear_midi()
        if address == '/pap/snapshot/save':
            return self.control.save_snapshot(str(value) if value else None)
        if address == '/pap/snapshot/load':
            return self.control.load_snapshot(str(value))
        return {'status': 'ignored', 'reason': f'unhandled address: {address}'}

    def serve_forever(self, *, timeout_seconds: float | None = None) -> dict[str, Any]:
        self.control.ensure_initialized()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        self.socket.settimeout(0.25)
        self.running = True
        self._write_daemon_status('running')
        started = time.time()
        handled = 0
        try:
            while self.running:
                if timeout_seconds is not None and (time.time() - started) >= timeout_seconds:
                    break
                try:
                    data, _ = self.socket.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    payload = json.loads(data.decode('utf-8'))
                except Exception:
                    continue
                self._handle_message(payload if isinstance(payload, dict) else {})
                handled += 1
        finally:
            if self.socket is not None:
                try:
                    self.socket.close()
                except OSError:
                    pass
            self._write_daemon_status('stopped', {'handled_messages': handled})
        return {'status': 'stopped', 'handled_messages': handled, 'host': self.host, 'port': self.port}
