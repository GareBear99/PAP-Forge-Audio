# Release Checklist

- Generate plugin workspace from prompt
- Confirm `pap/spec.json` and `pap/template_manifest.json` exist
- Create checkpoint
- Emit build plan
- Validate project
- Run build command in dry-run mode first
- If `JUCE_DIR` and toolchain are configured, run executed build step
- Archive export bundle
- Tag checkpoint and retain lineage graph
