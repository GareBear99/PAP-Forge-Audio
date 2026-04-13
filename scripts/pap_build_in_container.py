from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print('usage: pap_build_in_container.py <project_root> <checkpoint_id>')
        return 1
    project_root = Path(argv[0]).resolve()
    checkpoint_id = argv[1]
    build_dir = project_root / '.pap' / 'builds' / checkpoint_id / 'container_hook'
    build_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'status': 'declared',
        'project_root': str(project_root),
        'checkpoint_id': checkpoint_id,
        'juce_dir': os.environ.get('JUCE_DIR', ''),
        'note': 'Container hook executed. Extend this script to run docker build or cmake/ninja inside your owned environment.',
    }
    (build_dir / 'container_hook.json').write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
