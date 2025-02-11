.DEFAULT_GOAL := help
PROJECT_DIR := src/bricsauthenticator
TEST_DIR := tests/
SCRIPTS_DIR := scripts/

FORMAT_FILES := ${PROJECT_DIR} ${TEST_DIR} ${SCRIPTS_DIR}
LINT_FILES := ${PROJECT_DIR} ${TEST_DIR} ${SCRIPTS_DIR}

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
	@echo "  make coverage"

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

.PHONY: coverage
coverage:
	pytest --cov=bricsauthenticator --cov-report=term-missing --cov-report=xml --cov-report=html ${TEST_DIR}