PYTHON ?= python3
RUN := PYTHONPATH=$(CURDIR)/src $(PYTHON)
DB ?= var/lexicon.sqlite3
CASES ?= reports/search-cases.json
JMDICT ?= data/raw/jmdict-JMdict_e.gz
SUDACHI_DIR ?= data/raw/sudachidict-20260428

.PHONY: test lint check lexicon-fetch lexicon-build lexicon-build-demo lexicon-evaluate candidate-audit search-benchmark

test:
	$(RUN) -m pytest

lint:
	$(RUN) -m ruff check --no-cache src tests scripts

check: lint test
	$(RUN) scripts/check_docs.py

lexicon-fetch:
	$(RUN) -m wordquery_jp.cli fetch jmdict
	$(RUN) -m wordquery_jp.cli fetch sudachidict_small
	$(RUN) -m wordquery_jp.cli fetch sudachidict_core
	mkdir -p $(SUDACHI_DIR)
	unzip -q -o data/raw/sudachidict_small-small_lex.zip -d $(SUDACHI_DIR)
	unzip -q -o data/raw/sudachidict_core-core_lex.zip -d $(SUDACHI_DIR)

lexicon-build:
	test -f $(JMDICT)
	test -d $(SUDACHI_DIR)
	$(RUN) -m wordquery_jp.cli build --jmdict $(JMDICT) --sudachi $(SUDACHI_DIR) --output $(DB)

lexicon-build-demo:
	$(RUN) -m wordquery_jp.cli build --additions tests/fixtures/manual_additions.tsv --output $(DB)

lexicon-evaluate:
	$(RUN) -m wordquery_jp.cli evaluate --database $(DB) --output reports/quality.json

candidate-audit:
	$(RUN) -m wordquery_jp.cli candidate-audit --database $(DB)

search-benchmark:
	test -f $(CASES)
	$(RUN) -m wordquery_jp.cli search-benchmark --database $(DB) --cases $(CASES)
