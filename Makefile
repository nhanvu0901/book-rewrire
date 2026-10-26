.PHONY: dev install test test-neo4j test-openrouter lint format typecheck neo4j-up neo4j-down neo4j-shell ingest

install:
	uv sync --extra dev

test:
	uv run pytest

# Opt-in: checks connectivity and temporary Character writes against Neo4j.
test-neo4j:
	POV_NEO4J=1 uv run pytest -m neo4j

# Opt-in: sends a real, billable request using OPENROUTER_API_KEY from .env.
test-openrouter:
	POV_OPENROUTER=1 uv run pytest tests/test_openrouter_integration.py -v

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src tests

# Python and Docker Compose both read the repository's .env file.
COMPOSE := docker compose --env-file .env -f docker/compose.yml

# Start the local Docker Compose stack without waiting for its healthcheck.
dev:
	$(COMPOSE) up -d

# --wait blocks until the healthcheck is green. Project "book-clone-dev": see docker/compose.yml.
neo4j-up:
	$(COMPOSE) up -d --wait

neo4j-down:
	$(COMPOSE) down

# An interactive Cypher shell inside the container (type :exit to leave).
neo4j-shell:
	$(COMPOSE) exec neo4j sh -c 'cypher-shell -u neo4j -p "$${NEO4J_AUTH#neo4j/}"'

# Usage: make ingest BOOK=<book_id>
ingest:
	@test -n "$(BOOK)" || { echo "usage: make ingest BOOK=<book_id>"; exit 1; }
	uv run pov ingest $(BOOK)
