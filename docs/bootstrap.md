# PAP Bootstrap

Use `pap bootstrap <project_root>` after project init to write the local toolchain files that make operator handoff smoother.

Artifacts emitted:
- `.pap/toolchain/toolchain.json`
- `CMakeUserPresets.json`
- `.pap/scripts/build_local.sh`
- `.pap/scripts/build_container.sh`
- `.pap/runbooks/operator_quickstart.md`

Typical flow:

```bash
pap init demo ./workspace
pap bootstrap ./workspace/demo --juce-dir /path/to/JUCE
pap doctor ./workspace/demo
pap generate ./workspace/demo "Dark shimmer chorus with macro called Collapse"
pap report ./workspace/demo
```
