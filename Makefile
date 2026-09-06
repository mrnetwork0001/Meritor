# Meritor - reproduce everything a judge needs in one place.
PY ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: setup test demo web attest reproduce clean

setup:            ## create the venv and install dependencies
	python3 -m venv .venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r requirements.txt pytest

test:             ## run the full test suite
	$(PY) -m pytest -q

demo:             ## the fresh-session recall beat + deletion test, on real Sibyl Memory
	MEMORY_DRIVER=sibyl SIBYL_MEMORY_DB=.meritor/demo.db SIBYL_TENANT_ID=meritor-demo \
	  ./demo/fresh_session_demo.sh

web:              ## launch the landing page + live credit desk at http://127.0.0.1:8848
	$(PY) -m uvicorn web.server:app --host 127.0.0.1 --port 8848

attest:           ## publish a recalled tier to Base as an EAS attestation (needs a funded .env wallet)
	$(PY) -m meritor.cli attest 0xALPHA

reproduce: setup test demo   ## setup -> tests -> demo, from a clean clone

clean:            ## remove local memory databases
	rm -rf .meritor
