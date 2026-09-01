# prahari — one command to demo.
#
#   make setup    once, WITH a network. Installs everything.
#   make verify   prove the offline claim. Run this before you present.
#   make demo     build, seed, launch, open the browser. NO network needed.
#   make reset    clean known-good state in under 10 seconds.
#
# Everything except `setup` runs with the network off.

SHELL       := /bin/bash
PY          ?= python3
NPM         ?= npm
API_PORT    ?= 8000
WEB_PORT    ?= 5173
SEED_LIMIT  ?= 700
BACKEND     := backend
WEB         := web
RUN         := PYTHONPATH=.

.DEFAULT_GOAL := help
.PHONY: help setup setup-backend setup-web verify verify-static demo build seed reset \
        api web test lint model-manifest train-prep stop clean doctor check-web-deps

## ----------------------------------------------------------------------
help:
	@echo ""
	@echo "  prahari — offline SIF precursor detection"
	@echo "  ------------------------------------------------------------"
	@echo "  make setup     install everything (needs a network, run once)"
	@echo "  make verify    prove it runs offline (run before presenting)"
	@echo "  make demo      build + seed + launch + open browser"
	@echo "  make reset     clean known-good state, <10s"
	@echo "  make stop      stop anything on ports $(API_PORT)/$(WEB_PORT)"
	@echo ""
	@echo "  make test      backend test suite"
	@echo "  make doctor    what is installed, what is missing"
	@echo "  make api       backend only        make web    frontend only"
	@echo ""

## -- setup (the only target that needs a network) ----------------------
setup: setup-backend setup-web
	@echo ""
	@echo "  Setup complete. Now run:  make verify  &&  make demo"
	@echo ""

setup-backend:
	@echo "==> backend dependencies"
	$(PY) -m pip install -e ".[dev,ml]"

setup-web:
	@echo "==> frontend dependencies"
	cd $(WEB) && $(NPM) install --no-audit --no-fund

## -- verification -------------------------------------------------------
verify:
	@./scripts/verify_offline.sh

verify-static:
	@./scripts/verify_offline.sh --static

## -- the demo -----------------------------------------------------------
# Build first so the frontend is served as static files: no dev server, no
# file watcher, nothing that can decide to recompile mid-presentation.
demo: build seed
	@echo ""
	@echo "  Launching prahari. Ctrl-C stops both processes."
	@echo "  API  http://localhost:$(API_PORT)      UI  http://localhost:$(WEB_PORT)"
	@echo ""
	@bash scripts/launch_demo.sh

build:
	@echo "==> building the frontend"
	@if ! $(MAKE) --no-print-directory check-web-deps >/dev/null 2>&1; then \
		echo ""; \
		echo "  Frontend dependencies are missing or incomplete."; \
		echo "  A node_modules folder can exist and still be unusable (an"; \
		echo "  interrupted npm, a copied folder, a synced drive)."; \
		echo ""; \
		echo "  Fix (needs a network, once):   make setup"; \
		echo ""; \
		exit 1; \
	fi
	cd $(WEB) && $(NPM) run build

seed:
	@echo "==> seeding $(SEED_LIMIT) reports"
	@cd $(BACKEND) && $(RUN) $(PY) -m prahari.cli seed --limit $(SEED_LIMIT) 2>&1 \
		| grep -vE '^(prahari\.(ml|db):)' || true

reset:
	@./scripts/reset_demo.sh

stop:
	@for p in $(API_PORT) $(WEB_PORT); do \
		pids=$$(lsof -ti tcp:$$p 2>/dev/null || true); \
		if [ -n "$$pids" ]; then echo "  stopping $$pids on port $$p"; kill $$pids 2>/dev/null || true; fi; \
	done
	@echo "  ports clear"

## -- individual processes ----------------------------------------------
api:
	cd $(BACKEND) && $(RUN) $(PY) -m uvicorn prahari.main:app --host 127.0.0.1 --port $(API_PORT) --reload

web:
	cd $(WEB) && $(NPM) run dev

# Resolve a few packages rather than trusting the directory's existence.
check-web-deps:
	@cd $(WEB) && node -e "['react','react-dom','react-router-dom','recharts','lucide-react','tailwind-merge','vite','typescript'].forEach(m=>require.resolve(m+'/package.json'))" 2>/dev/null

## -- development --------------------------------------------------------
test:
	cd $(BACKEND) && $(RUN) $(PY) -m pytest tests -q

lint:
	cd $(WEB) && $(NPM) run typecheck

model-manifest:
	@./scripts/model_manifest.sh

train-prep:
	cd $(BACKEND) && $(RUN) $(PY) -m prahari.data.generator --n 3000 --seed 42
	cd $(BACKEND) && $(RUN) $(PY) -m prahari.ml.training.prepare_data

doctor:
	@echo ""
	@echo "  python      $$($(PY) --version 2>&1)"
	@echo "  node        $$(node --version 2>/dev/null || echo 'NOT FOUND')"
	@echo "  npm         $$($(NPM) --version 2>/dev/null || echo 'NOT FOUND')"
	@for m in fastapi sqlalchemy pydantic uvicorn alembic; do \
		$(PY) -c "import $$m" 2>/dev/null && echo "  py:$$m$$(printf '%*s' $$((10-$${#m})) '') ok" || echo "  py:$$m  MISSING"; \
	done
	@$(MAKE) --no-print-directory check-web-deps >/dev/null 2>&1 \
		&& echo "  web deps    ok" \
		|| echo "  web deps    MISSING or INCOMPLETE (make setup)"
	@[ -s data/synthetic_reports.jsonl ] && echo "  corpus      ok ($$(wc -l < data/synthetic_reports.jsonl | tr -d ' ') reports)" || echo "  corpus      MISSING"
	@[ -f models/prahari.onnx ] && echo "  onnx model  present" || echo "  onnx model  absent (keyword fallback — supported)"
	@echo ""

clean: stop
	@rm -rf $(WEB)/dist $(BACKEND)/.pytest_cache 2>/dev/null || true
	@find $(BACKEND) -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "  build artefacts removed"
