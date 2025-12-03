.DEFAULT_GOAL := help
.PHONY: help install install-dev test check format lint type-check security-check clean changelog deploy-docs benchmark benchmark-pytest benchmark-asv

help:  ## Display this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package in development mode
	pip install -e .

install-dev:  ## Install the package with development dependencies
	pip install -e '.[dev]'

test:  ## Run tests with pytest
	pytest

check: lint format type-check  ## Run all checks (lint, format, type-check)

format:  ## Format code with ruff
	ruff format src/ tests/

lint:  ## Lint code with ruff
	ruff check --fix src/ tests/

type-check:  ## Type check with pyright
	pyright

clean:  ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .tox/
	rm -rf .asv/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

changelog:  ## compile changelog
	git cliff --output CHANGELOG.md $(if $(bump),--tag $(bump))

deploy-docs:  ## build and publish documentation
	mkdocs gh-deploy

benchmark:  ## Run all benchmarks
	@echo "Running benchmark suite..."
	@$(MAKE) benchmark-pytest
	@$(MAKE) benchmark-asv

benchmark-pytest:  ## Run pytest-based benchmarks
	pip install -e '.[bench]'
	pytest .benchmarks/test_benchmarks.py -v --benchmark-only --benchmark-sort=fullname

benchmark-asv:  ## Run ASV benchmarks (requires asv installation)
	@echo "Setting up asv benchmarks..."
	@echo "To run ASV benchmarks, first install asv: pip install asv"
	@echo "Then run: asv run --verbose"
	@echo "To show results: asv show"
	@echo "To run specific benchmark: asv run --bench MemoryStorageSuite.time_upload_small"
