PYTHON ?= python3

.PHONY: test validate smoke radio score references keyframes film

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) -m pipeline.validate

smoke:
	$(PYTHON) -m pipeline.smoke

radio: validate
	$(PYTHON) -m pipeline.radio

score:
	$(PYTHON) -m pipeline.music status

references: validate
	$(PYTHON) -m pipeline.references

keyframes: validate
	$(PYTHON) -m pipeline.keyframes

film: validate
	$(PYTHON) -m pipeline.film
