# =============================================================================
# Personalized Networking Assistant — Makefile
# =============================================================================
# Usage: make <target>
#
# Requires GNU make (included on Linux/macOS; install via Git for Windows or
# via `choco install make` on Windows).
#
# All commands assume the virtualenv is active. On Windows PowerShell, use:
#   .venv\Scripts\Activate.ps1
# then run: make <target>

.PHONY: help install dev-api dev-ui test test-watch lint clean format

# Default target
.DEFAULT_GOAL := help

# Shell configuration
SHELL := bash

# Detect OS for cross-platform compatibility
ifeq ($(OS),Windows_NT)
    PYTHON := python
    PIP    := pip
    SEP    := \\
else
    PYTHON := python3
    PIP    := pip3
    SEP    := /
endif

# Application entry points
API_MODULE  := backend.main:app
UI_ENTRY    := frontend/app.py
TEST_DIR    := backend/tests

# Ports
API_PORT    := 8000
UI_PORT     := 8501

# ============================================================
# Help
# ============================================================

help:  ## Show this help message
	@echo ""
	@echo "  Personalized Networking Assistant — Development Commands"
	@echo "  ========================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================================
# Installation
# ============================================================

install:  ## Install all Python dependencies from requirements.txt
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-cpu:  ## Install dependencies with CPU-only PyTorch (smaller download)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# ============================================================
# Development servers
# ============================================================

dev-api:  ## Start the FastAPI backend with hot-reload on port 8000
	@echo "Starting FastAPI backend on http://localhost:$(API_PORT)..."
	@echo "Docs available at http://localhost:$(API_PORT)/docs"
	uvicorn $(API_MODULE) \
		--host 0.0.0.0 \
		--port $(API_PORT) \
		--reload \
		--log-level info

dev-ui:  ## Start the Streamlit frontend on port 8501
	@echo "Starting Streamlit frontend on http://localhost:$(UI_PORT)..."
	streamlit run $(UI_ENTRY) \
		--server.port $(UI_PORT) \
		--server.address localhost \
		--server.headless false \
		--browser.gatherUsageStats false

# ============================================================
# Testing
# ============================================================

test:  ## Run all pytest tests with verbose output
	pytest $(TEST_DIR) -v --tb=short

test-watch:  ## Run tests in watch mode (requires pytest-watch: pip install pytest-watch)
	ptw $(TEST_DIR) -- -v --tb=short

test-coverage:  ## Run tests with coverage report (requires pytest-cov)
	pytest $(TEST_DIR) -v \
		--cov=backend \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--tb=short
	@echo ""
	@echo "HTML coverage report: htmlcov/index.html"

test-api:  ## Run only API integration tests
	pytest $(TEST_DIR)/test_api_routes.py -v --tb=short

test-services:  ## Run only service unit tests
	pytest \
		$(TEST_DIR)/test_event_analyzer.py \
		$(TEST_DIR)/test_topic_generator.py \
		$(TEST_DIR)/test_fact_checker.py \
		-v --tb=short

# ============================================================
# Code Quality
# ============================================================

lint:  ## Run ruff linter (install with: pip install ruff)
	ruff check backend/ frontend/

lint-fix:  ## Auto-fix ruff lint issues
	ruff check --fix backend/ frontend/

format:  ## Format code with ruff formatter
	ruff format backend/ frontend/

type-check:  ## Run mypy type checking (install with: pip install mypy)
	mypy backend/ --ignore-missing-imports

# ============================================================
# Database
# ============================================================

db-reset:  ## Delete the SQLite database (WARNING: destroys all data)
	@echo "Deleting networking_assistant.db..."
	rm -f networking_assistant.db
	@echo "Database deleted. It will be recreated on next API startup."

# ============================================================
# Clean
# ============================================================

clean:  ## Remove build artifacts, cache files, and the SQLite database
	@echo "Cleaning project..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc"      -delete 2>/dev/null || true
	find . -type f -name "*.pyo"      -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"    -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache"   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov"       -exec rm -rf {} + 2>/dev/null || true
	rm -f networking_assistant.db
	@echo "Clean complete."

# ============================================================
# Environment setup
# ============================================================

env-setup:  ## Copy .env.example to .env (if .env doesn't exist)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env created from .env.example"; \
		echo "  Edit .env and set GEMINI_API_KEY before running."; \
	else \
		echo ".env already exists — skipping."; \
	fi

# ============================================================
# Info
# ============================================================

info:  ## Print environment information
	@echo ""
	@echo "  Python:   $(shell $(PYTHON) --version)"
	@echo "  Pip:      $(shell $(PIP) --version)"
	@echo "  API URL:  http://localhost:$(API_PORT)"
	@echo "  UI URL:   http://localhost:$(UI_PORT)"
	@echo "  Docs URL: http://localhost:$(API_PORT)/docs"
	@echo ""
