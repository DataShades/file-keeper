.DEFAULT_GOAL := help
.PHONY: help install install-dev test check format lint type-check security-check changelog deploy-docs

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

changelog:  ## compile changelog
	git cliff --output CHANGELOG.md $(if $(bump),--tag $(bump))

deploy-docs:  ## build and publish documentation
	mkdocs gh-deploy
