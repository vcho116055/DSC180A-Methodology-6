.PHONY: all data features train test clean model check-model

PYTHON ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)

# --- The pipeline ----------------------------------------------------------
all: data features train

data:
	$(PYTHON) -m src.ingest

features:
	$(PYTHON) -m src.features

train:
	$(PYTHON) -m src.train

test:
	$(PYTHON) -m pytest tests/ -q

clean:
	rm -f data/processed/*.parquet reports/metrics.json reports/*.png

# --- The agent model (open weights, local) ----------------------------------
# Builds `bikeshare-coder`: the base model plus a 64k context window, which
# Claude Code needs and Ollama does not give you by default. Pick a larger
# BASE if your machine has the memory (see README.md).
BASE ?= qwen3.5:9b

model:
	ollama pull $(BASE)
	sed "s|^FROM .*|FROM $(BASE)|" model/Modelfile > model/.Modelfile.build
	ollama create bikeshare-coder -f model/.Modelfile.build && rm -f model/.Modelfile.build

check-model:
	bash model/check.sh
