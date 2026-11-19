# Postgres 16 + pgvector with the portal data baked in: on first start (empty volume) the official
# entrypoint restores the full portal database. No download, no ingest.
FROM pgvector/pgvector:pg16
LABEL org.opencontainers.image.source="https://github.com/qh-fol-in-luv-w-data/uiuc-research-portal"
LABEL org.opencontainers.image.description="UIUC Research Portal database: OpenAlex works (Nov 2024 - Nov 2026), faculty, links, embeddings, stats"
ENV POSTGRES_USER=portal POSTGRES_PASSWORD=portal POSTGRES_DB=portal
COPY dump/portal-image.sql.gz /docker-entrypoint-initdb.d/10-portal.sql.gz
