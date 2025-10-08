.PHONY: format lint test docs docs-serve docs-watch upload-to-test upload docs-watch docs-serve

format: lint
	uv run -- ruff format

lint:
	uv run -- ruff check --fix

test:
	uv run -- pytest -vv --tb=short

build:
	uv run -- uv-build

upload-to-test:
	uv run -- twine upload --respository testpypi dist/*

upload:
	uv run -- twine upload dist/*

docs:
	uv run sphinx-build -b html docs docs/_build/html

docs-serve:
	uv run sphinx-autobuild docs docs/_build/html --open-browser --port 8080

docs-watch:
	uv run sphinx-autobuild docs docs/_build/html --watch src/ --port 8080