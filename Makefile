.PHONY: db-up migrate ingest test dump restore

db-up:
	docker compose up -d --wait db

migrate:
	uv run python -m ingest migrate

ingest:
	uv run python -m ingest all

test:
	uv run pytest -q

dump:
	mkdir -p db/dump
	docker compose exec -T db pg_dump -U portal --no-owner --clean --if-exists portal | gzip > db/dump/portal.sql.gz

restore:
	gunzip -c db/dump/portal.sql.gz | docker compose exec -T db psql -U portal -d portal -q
