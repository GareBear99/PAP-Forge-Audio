from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

from pap.control_daemon import PAPControlDaemon
from pap.project import PAPProject


def _init_and_generate(tmp_path: Path):
    project = PAPProject.init('demo', tmp_path, template_root=Path(__file__).resolve().parents[1] / 'templates' / 'juce_effect_basic')
    project.generate_from_prompt('Dark shimmer chorus with macro called Collapse')
    return project


def test_control_automation_executes(tmp_path: Path):
    project = _init_and_generate(tmp_path)
    timeline = [
        {'at': 0.0, 'kind': 'set', 'parameter_id': 'mix', 'value': 0.25},
        {'at': 0.01, 'kind': 'set', 'parameter_id': 'mix', 'value': 0.75},
    ]
    result = project.control_automation(timeline, speed=100.0)
    assert result['events_executed'] == 2
    state = json.loads((project.root / '.pap' / 'control' / 'runtime_state.json').read_text())
    assert abs(state['parameters']['mix'] - 0.75) < 1e-6


def test_control_daemon_applies_udp_message(tmp_path: Path):
    project = _init_and_generate(tmp_path)
    daemon = PAPControlDaemon(project.root, host='127.0.0.1', port=9137)
    thread = threading.Thread(target=lambda: daemon.serve_forever(timeout_seconds=0.4), daemon=True)
    thread.start()
    time.sleep(0.05)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(json.dumps({'address': '/pap/param/mix', 'value': 0.61}).encode('utf-8'), ('127.0.0.1', 9137))
    finally:
        sock.close()
    thread.join(timeout=2.0)
    state = json.loads((project.root / '.pap' / 'control' / 'runtime_state.json').read_text())
    assert abs(state['parameters']['mix'] - 0.61) < 1e-6


def test_control_transport_snapshot_and_monitor(tmp_path: Path):
    project = _init_and_generate(tmp_path)
    project.control_transport(playing=True, bpm=132.0, bar=9, beat=1)
    project.control_marker('drop', position_beats=32.0, color='purple')
    snap = project.control_save_snapshot('verse_a')
    monitored = project.control_monitor(count=2, interval=0.0)
    assert monitored['status'] == 'ok'
    assert len(monitored['samples']) == 2
    state = project.control_status()['runtime_state']
    assert state['transport']['playing'] is True
    assert state['transport']['bpm'] == 132.0
    assert state['markers'][-1]['name'] == 'drop'
    assert (project.root / snap['path']).exists()


def test_control_daemon_transport_message(tmp_path: Path):
    project = _init_and_generate(tmp_path)
    daemon = PAPControlDaemon(project.root, host='127.0.0.1', port=9138)
    thread = threading.Thread(target=lambda: daemon.serve_forever(timeout_seconds=0.4), daemon=True)
    thread.start()
    time.sleep(0.05)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(json.dumps({'address': '/pap/transport', 'value': {'playing': True, 'bpm': 140.0}}).encode('utf-8'), ('127.0.0.1', 9138))
    finally:
        sock.close()
    thread.join(timeout=2.0)
    state = json.loads((project.root / '.pap' / 'control' / 'runtime_state.json').read_text())
    assert state['transport']['playing'] is True
    assert state['transport']['bpm'] == 140.0
