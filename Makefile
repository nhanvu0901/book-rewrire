.PHONY: install test test-books lint format typecheck db-up db-down

install:
	uv sync --extra dev

test:
	uv run pytest

# Opt-in: runs the real books in BOOK_CLONE_DATA_DIR/books (they are not in git).
test-books:
	POV_LOCAL_BOOKS=1 uv run pytest -m local_books

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src tests

# The compose file wants NEO4J_PASSWORD: take it from the secrets file when that file exists.
SECRETS := $(wildcard $(HOME)/.config/book-clone/secrets.env)
COMPOSE := docker compose -f docker/compose.yml $(if $(SECRETS),--env-file $(SECRETS),)

# --wait blocks until every healthcheck is green. Project "book-clone-dev": see docker/compose.yml.
db-up:
	$(COMPOSE) up -d --wait

db-down:
	$(COMPOSE) down
