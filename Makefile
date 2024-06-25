.DEFAULT_GOAL := help
PROJECT_DIR := src/mappingauthenticator
TEST_DIR := tests/

FORMAT_FILES := ${PROJECT_DIR} ${TEST_DIR}
LINT_FILES := ${PROJECT_DIR} ${TEST_DIR}

# Tooling - configure in pyproject.toml
isort := isort
black := black
autoflake := autoflake --recursive --quiet
pytest := pytest --verbose

.PHONY: help
help:
	@echo "Please invoke make with a valid goal:"
	@echo "  make format"
	@echo "  make lint"
	@echo "  make test"

.PHONY: format
format:
	${autoflake} --in-place ${FORMAT_FILES}
	${isort} ${FORMAT_FILES}
	${black} ${FORMAT_FILES}

.PHONY: lint
lint: 
	${autoflake} --check ${LINT_FILES}
	${isort} --check ${LINT_FILES}
	${black} --check ${LINT_FILES}

.PHONY: test
test:
	${pytest} ${TEST_DIR}
