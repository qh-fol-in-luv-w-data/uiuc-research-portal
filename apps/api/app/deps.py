from collections.abc import Iterator

import psycopg
from fastapi import Request


def get_conn(request: Request) -> Iterator[psycopg.Connection]:
    with request.app.state.pool.connection() as conn:
        yield conn
