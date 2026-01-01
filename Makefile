.PHONY: format lint test docs docs-serve docs-watch upload-to-test upload publish docs-watch docs-serve install

version ?= $(shell grep '^version =' pyproject.toml | cut -d'"' -f2)

format: lint
	uv run -- ruff format

lint:
	uv run -- ruff check --fix

test:
	uv run -- pytest -vv --tb=short -n auto

install:
	uv sync --frozen --compile-bytecode --all-extras

upgrade:
	uv sync --upgrade --all-extras

build:
	rm -rf dist/ build/ *.egg-info/
	uv build

upload-to-test:
	uv run -- twine upload --repository testpypi dist/*

upload: build
	uv run -- twine upload dist/*

docs:
	uv run sphinx-build -b html docs docs/_build/html

docs-serve:
	uv run sphinx-autobuild docs docs/_build/html --open-browser --port 8080

publish: format test build upload
	git tag -a v$(version) -m "Release v$(version)"
	git push origin v$(version)
	git push origin main