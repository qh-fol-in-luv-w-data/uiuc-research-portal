CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE topics (
  id text PRIMARY KEY,
  display_name text NOT NULL,
  subfield text,
  field text,
  domain text
);

CREATE TABLE institutions (
  id text PRIMARY KEY,
  display_name text,
  country_code text,
  type text
);

CREATE TABLE authors (
  id text PRIMARY KEY,
  display_name text NOT NULL,
  orcid text,
  works_count_in_set integer NOT NULL DEFAULT 0
);

CREATE TABLE works (
  id text PRIMARY KEY,
  doi text,
  title text NOT NULL,
  abstract text,
  publication_date date,
  type text,
  language text,
  cited_by_count integer NOT NULL DEFAULT 0,
  is_oa boolean NOT NULL DEFAULT false,
  oa_url text,
  venue_name text,
  venue_type text,
  primary_topic_id text REFERENCES topics(id),
  is_outlier boolean NOT NULL DEFAULT false,
  outlier_reason text,
  tsv tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(abstract, '')), 'B')
  ) STORED,
  embedding vector(1024)
);

CREATE TABLE authorships (
  work_id text NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  author_id text NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
  position text,
  is_uiuc boolean NOT NULL DEFAULT false,
  raw_affiliation text,
  PRIMARY KEY (work_id, author_id)
);

CREATE TABLE work_institutions (
  work_id text NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  institution_id text NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  PRIMARY KEY (work_id, institution_id)
);

CREATE TABLE work_topics (
  work_id text NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  topic_id text NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  score real,
  PRIMARY KEY (work_id, topic_id)
);

CREATE TABLE faculty (
  id serial PRIMARY KEY,
  email text NOT NULL UNIQUE,
  name text NOT NULL,
  photo_url text,
  position text,
  keywords_raw text[] NOT NULL DEFAULT '{}',
  keywords text[] NOT NULL DEFAULT '{}',
  keywords_text text NOT NULL DEFAULT '',
  primary_field text,
  tsv tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', keywords_text), 'A') ||
    setweight(to_tsvector('english', coalesce(name, '')), 'B')
  ) STORED,
  keyword_embedding vector(1024),
  embedding vector(1024)
);

CREATE TABLE author_profile (
  author_id text PRIMARY KEY REFERENCES authors(id) ON DELETE CASCADE,
  profile_text text NOT NULL,
  embedding vector(1024) NOT NULL
);

CREATE TABLE faculty_author_link (
  faculty_id integer NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
  author_id text NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
  confidence real NOT NULL,
  method text NOT NULL,
  PRIMARY KEY (faculty_id, author_id)
);

CREATE TABLE stats_cache (
  key text PRIMARY KEY,
  payload jsonb NOT NULL,
  computed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX works_tsv_idx ON works USING gin (tsv);
CREATE INDEX works_embedding_idx ON works USING hnsw (embedding vector_cosine_ops);
CREATE INDEX works_pubdate_idx ON works (publication_date);
CREATE INDEX works_cited_idx ON works (cited_by_count);
CREATE INDEX works_primary_topic_idx ON works (primary_topic_id);
CREATE INDEX authorships_author_idx ON authorships (author_id);
CREATE INDEX work_institutions_inst_idx ON work_institutions (institution_id);
CREATE INDEX work_topics_topic_idx ON work_topics (topic_id);
CREATE INDEX faculty_tsv_idx ON faculty USING gin (tsv);
CREATE INDEX faculty_embedding_idx ON faculty USING hnsw (embedding vector_cosine_ops);
