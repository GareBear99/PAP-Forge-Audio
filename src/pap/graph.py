from __future__ import annotations

from pathlib import Path

from .manifests import write_json


class LineageGraph:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / '.pap' / 'graphs'
        self.root.mkdir(parents=True, exist_ok=True)

    def emit(self, checkpoints: list[dict[str, object]], branches: dict[str, str | None]) -> dict[str, object]:
        nodes = []
        edges = []
        for cp in checkpoints:
            nodes.append({
                'id': cp['checkpoint_id'],
                'label': cp['plugin_name'],
                'created_at': cp['created_at'],
                'template_id': cp['template_id'],
            })
            if cp.get('parent_id'):
                edges.append({'from': cp['parent_id'], 'to': cp['checkpoint_id']})
        payload = {'nodes': nodes, 'edges': edges, 'branches': branches}
        write_json(self.root / 'lineage.json', payload)
        return payload
