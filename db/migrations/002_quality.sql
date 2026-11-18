ALTER TABLE works ADD COLUMN duplicate_of text;
ALTER TABLE institutions ADD COLUMN is_uiuc_unit boolean NOT NULL DEFAULT false;
CREATE INDEX works_duplicate_idx ON works (duplicate_of) WHERE duplicate_of IS NOT NULL;
