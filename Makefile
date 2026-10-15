.PHONY: install test test-books test-neo4j lint format typecheck neo4j-up neo4j-down neo4j-shell ingest

install:
	uv sync --extra dev

test:
	uv run pytest

# Opt-in: runs the real books in BOOK_CLONE_DATA_DIR/books (they are not in git).
test-books:
	POV_LOCAL_BOOKS=1 uv run pytest -m local_books

# Opt-in: writes a throwaway book into the dev Neo4j (needs `make neo4j-up` first).
test-neo4j:
	POV_NEO4J=1 uv run pytest -m neo4j

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

# --wait blocks until the healthcheck is green. Project "book-clone-dev": see docker/compose.yml.
neo4j-up:
	$(COMPOSE) up -d --wait

# Stopping needs no password, but Compose still reads the file: give it a placeholder.
neo4j-down:
	NEO4J_PASSWORD="$${NEO4J_PASSWORD:-unused-placeholder}" $(COMPOSE) down

# An interactive Cypher shell inside the container (type :exit to leave).
neo4j-shell:
	$(COMPOSE) exec neo4j sh -c 'cypher-shell -u neo4j -p "$${NEO4J_AUTH#neo4j/}"'

# Usage: make ingest BOOK=the-lion-the-witch-and-the-wardrobe
ingest:
	@test -n "$(BOOK)" || { echo "usage: make ingest BOOK=<book_id>"; exit 1; }
	uv run pov ingest $(BOOK)
