.PHONY: up down logs restore dump ingest test test-api test-web e2e screenshots image-dump publish eval attacks

# Ports default to 3000 (web) / 8010 (api); override e.g. `make up WEB_PORT=3100`
WEB_PORT ?= 3000
export WEB_PORT

up:            ## build and start everything; first run restores data and pulls Ollama models
	docker compose up -d --build --wait

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

restore:       ## load the prebuilt database dump (db/dump/portal.sql.gz)
	docker compose up -d --wait db
	gunzip -c db/dump/portal.sql.gz | docker compose exec -T db psql -U portal -d portal -q

dump:
	mkdir -p db/dump
	docker compose exec -T db pg_dump -U portal --no-owner --clean --if-exists portal | gzip -9 > db/dump/portal.sql.gz

ingest:        ## rebuild the database from OpenAlex + the faculty CSV (about 40 minutes, mostly embeddings)
	uv run python -m ingest all

test: test-api test-web

test-api:
	uv run pytest -q

test-web:
	cd apps/web && npm test

e2e:           ## end-to-end tests against the running stack, using the local Chrome
	cd apps/web && E2E_BASE_URL=http://localhost:$(WEB_PORT) npx playwright test

screenshots:
	cd apps/web && E2E_BASE_URL=http://localhost:$(WEB_PORT) node scripts/screenshots.mjs

# ---- release: multi-arch images on GHCR (needs `gh auth refresh -s write:packages` and docker login) ----
REGISTRY ?= ghcr.io/qh-fol-in-luv-w-data
TAG ?= latest
PLATFORMS ?= linux/amd64,linux/arm64
SOURCE := https://github.com/qh-fol-in-luv-w-data/uiuc-research-portal
# index-level annotation: lets GitHub link the multi-arch packages to the repository
ANNOTATE := --annotation "index:org.opencontainers.image.source=$(SOURCE)"

image-dump:    ## dump without DROP statements, baked into the db image
	docker compose exec -T db pg_dump -U portal --no-owner --no-privileges portal | gzip -9 > db/dump/portal-image.sql.gz

publish:       ## build and push db, api and web images for amd64 + arm64
	docker buildx build --platform $(PLATFORMS) $(ANNOTATE) -t $(REGISTRY)/uiuc-research-portal-db:$(TAG) --push db
	docker buildx build --platform $(PLATFORMS) $(ANNOTATE) -t $(REGISTRY)/uiuc-research-portal-api:$(TAG) -f apps/api/Dockerfile --push .
	docker buildx build --platform $(PLATFORMS) $(ANNOTATE) -t $(REGISTRY)/uiuc-research-portal-web:$(TAG) --push apps/web

eval:
	uv run python eval/run.py

attacks:
	uv run python eval/attacks.py
