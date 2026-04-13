# PAP Forge Operations

## Recommended local flow

```bash
PYTHONPATH=src python -m pap.cli init demo workspace
PYTHONPATH=src python -m pap.cli generate workspace/demo "Dark shimmer chorus with macro called Collapse"
PYTHONPATH=src python -m pap.cli doctor workspace/demo
PYTHONPATH=src python -m pap.cli status workspace/demo
PYTHONPATH=src python -m pap.cli plan workspace/demo <checkpoint_id>
PYTHONPATH=src python -m pap.cli release workspace/demo <checkpoint_id>
PYTHONPATH=src python -m pap.cli export workspace/demo
```

## Container note

The builder Dockerfile and hook are declared in this repository. Running a true JUCE build still depends on the project owner supplying JUCE and target platform toolchains.
