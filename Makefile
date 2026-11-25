PYTHON ?= python3

.PHONY: test validate smoke radio

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) -m pipeline.validate

smoke:
	$(PYTHON) -m pipeline.smoke

radio: validate
	$(PYTHON) -m pipeline.radio
