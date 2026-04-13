from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class GenerationRequest:
    prompt: str
    requested_plugin_type: str = 'effect'
    target_formats: list[str] = field(default_factory=lambda: ['VST3'])
    template_id: str | None = None
    preferred_branch: str = 'main'
    style_reference: str | None = None
    cpu_budget_hint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class MutationRequest:
    checkpoint_id: str
    prompt: str
    preserve_sound_identity: bool = True
    target_branch: str = 'main'

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ArtifactRecord:
    kind: str
    path: str
    checksum: str
    bytes_size: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class BuildPlan:
    checkpoint_id: str
    project_name: str
    plugin_name: str
    template_id: str
    container_image: str
    target_formats: list[str]
    notes: list[str] = field(default_factory=list)
    builder_mode: str = 'declared'
    environment: dict[str, str] = field(default_factory=dict)
    output_layout: dict[str, str] = field(default_factory=dict)
    commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class BuildExecutionReceipt:
    status: str
    checkpoint_id: str
    executed: bool
    output_dir: str
    notes: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class BuildReceipt:
    status: str
    checkpoint_id: str
    plugin_name: str
    template_id: str
    written_files: list[str]
    notes: list[str] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    build_plan: BuildPlan | None = None
    preview: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.build_plan is None:
            payload['build_plan'] = None
        return payload
