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