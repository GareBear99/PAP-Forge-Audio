from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from .specs import PluginSpec


@dataclass(slots=True)
class PreviewReceipt:
    wav_path: str
    duration_seconds: float
    sample_rate: int
    peak: float
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            'wav_path': self.wav_path,
            'duration_seconds': self.duration_seconds,
            'sample_rate': self.sample_rate,
            'peak': self.peak,
            'notes': list(self.notes),
        }


class PreviewRenderer:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / '.pap' / 'previews'
        self.root.mkdir(parents=True, exist_ok=True)

    def render(self, checkpoint_id: str, spec: PluginSpec) -> PreviewReceipt:
        out_dir = self.root / checkpoint_id
        out_dir.mkdir(parents=True, exist_ok=True)
        wav_path = out_dir / 'preview.wav'
        sample_rate = 44100
        duration = 2.5 if spec.plugin_type == 'effect' else 3.0
        audio = self._render_audio(spec, sample_rate=sample_rate, duration=duration)
        peak = max(max(audio), -min(audio), 1e-9)
        normalized = [max(-0.95, min(0.95, s / max(peak, 1e-9) * 0.8)) for s in audio]
        with wave.open(str(wav_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = b''.join(struct.pack('<h', int(sample * 32767.0)) for sample in normalized)
            wf.writeframes(frames)
        return PreviewReceipt(
            wav_path=str(wav_path.relative_to(self.project_root)),
            duration_seconds=duration,
            sample_rate=sample_rate,
            peak=float(max(abs(s) for s in normalized)),
            notes=[
                'Prompt-derived offline preview render.',
                'This preview is for checkpoint auditioning, not plugin-binary validation.',
            ],
        )

    def _render_audio(self, spec: PluginSpec, *, sample_rate: int, duration: float) -> list[float]:
        frames = int(sample_rate * duration)
        if spec.plugin_type == 'synth':
            return self._render_synth(spec, sample_rate, frames)
        return self._render_effect(spec, sample_rate, frames)

    def _render_synth(self, spec: PluginSpec, sample_rate: int, frames: int) -> list[float]:
        freqs = [110.0, 138.59, 164.81]
        chorus = 'chorus' in spec.description.lower() or 'ensemble' in spec.description.lower()
        drift = 0.0015 if 'analog' in spec.description.lower() or 'drift' in spec.description.lower() else 0.0
        out: list[float] = []
        for i in range(frames):
            t = i / sample_rate
            env = min(1.0, t / 0.08) * max(0.0, 1.0 - max(0.0, t - duration_soft(frames, sample_rate)) / 0.9)
            sample = 0.0
            for idx, f in enumerate(freqs):
                det = 1.0 + drift * math.sin(2.0 * math.pi * (0.17 + idx * 0.03) * t)
                phase = 2.0 * math.pi * f * det * t
                sample += 0.32 * math.sin(phase)
                sample += 0.10 * math.sin(phase * 2.0)
                if chorus:
                    sample += 0.08 * math.sin(phase * (1.003 + idx * 0.001))
            shimmer = 0.12 * math.sin(2.0 * math.pi * 880.0 * t) if 'shimmer' in spec.description.lower() else 0.0
            out.append((sample / len(freqs) + shimmer) * env)
        return simple_delay(out, sample_rate, wet=0.18 if chorus else 0.08, feedback=0.2)

    def _render_effect(self, spec: PluginSpec, sample_rate: int, frames: int) -> list[float]:
        src = []
        for i in range(frames):
            t = i / sample_rate
            src.append(0.45 * math.sin(2.0 * math.pi * 220.0 * t) + 0.2 * math.sin(2.0 * math.pi * 330.0 * t))
        desc = spec.description.lower()
        if 'chorus' in desc or 'ensemble' in desc:
            mod = [0.0] * frames
            for i in range(frames):
                t = i / sample_rate
                mod[i] = 0.0035 + 0.0025 * math.sin(2.0 * math.pi * 0.8 * t)
            out = comb_chorus(src, sample_rate, mod)
        elif 'delay' in desc or 'echo' in desc:
            out = simple_delay(src, sample_rate, wet=0.35, feedback=0.35)
        elif 'phaser' in desc or 'flanger' in desc:
            out = comb_chorus(src, sample_rate, [0.0008 + 0.0007 * math.sin(2.0 * math.pi * 0.3 * i / sample_rate) for i in range(frames)])
        else:
            out = list(src)
        if 'tape' in desc or 'analog' in desc or 'drive' in desc:
            out = [math.tanh(s * 1.4) * 0.8 for s in out]
        if 'reverb' in desc or 'shimmer' in desc:
            out = simple_delay(out, sample_rate, wet=0.2, feedback=0.25)
        return out


def duration_soft(frames: int, sample_rate: int) -> float:
    return max(0.4, frames / sample_rate - 1.2)


def simple_delay(src: list[float], sample_rate: int, *, wet: float, feedback: float) -> list[float]:
    delay = max(1, int(sample_rate * 0.17))
    out = [0.0] * len(src)
    for i, sample in enumerate(src):
        delayed = out[i - delay] if i >= delay else 0.0
        out[i] = sample * (1.0 - wet) + delayed * wet
        out[i] += sample * 0.3
        if i >= delay:
            out[i] += out[i - delay] * feedback * 0.25
    return out


def comb_chorus(src: list[float], sample_rate: int, mod_delays: list[float]) -> list[float]:
    out = [0.0] * len(src)
    for i, sample in enumerate(src):
        delay_samples = int(max(1, mod_delays[i] * sample_rate))
        delayed = src[i - delay_samples] if i >= delay_samples else 0.0
        out[i] = sample * 0.72 + delayed * 0.28
    return out
