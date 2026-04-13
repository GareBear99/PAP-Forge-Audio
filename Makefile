PYTHON ?= python

.PHONY: test
test:
	$(PYTHON) -m pytest -q

.PHONY: demo
demo:
	PYTHONPATH=src $(PYTHON) -m pap.cli init demo workspace
	PYTHONPATH=src $(PYTHON) -m pap.cli generate workspace/demo "Dark shimmer chorus with macro called Collapse"

.PHONY: package
package:
	cd .. && zip -qr PAP_Forge_repo.zip papwork
