.PHONY: fmt lint all build publish

TWINE_USER ?= __token__
TWINE_PASSWORD_CMD ?= pass dev/pypy-tokens/all
VERSION := $(shell python -c "import sqlbind_t; print(sqlbind_t.version)")
WHL := dist/sqlbind_t-$(VERSION)-py3-none-any.whl

fmt:
	ruff check --select I --fix
	ruff format

lint:
	ruff check
	mypy

all: fmt lint

build:
	rm -rf build || true
	python -m build -nw .

$(WHL):
	python -m build -nw .

publish: $(WHL)
	TWINE_PASSWORD="$$( $(TWINE_PASSWORD_CMD) )" twine upload -u "$(TWINE_USER)" "$(WHL)"
