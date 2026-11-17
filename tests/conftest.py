import os

import pytest

from ingest.db import apply_migrations, connect

TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://portal:portal@localhost:55432/portal_test")


@pytest.fixture
def db():
    conn = connect(TEST_URL)
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    conn.close()
    conn = connect(TEST_URL)
    apply_migrations(conn)
    yield conn
    conn.rollback()
    conn.close()
