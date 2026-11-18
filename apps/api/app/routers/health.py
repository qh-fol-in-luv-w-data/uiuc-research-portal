from fastapi import APIRouter, Depends, Request

from ..deps import get_conn
from ..schemas import Health

router = APIRouter()


def _installed(required: str, models: list[str]) -> bool:
    # "bge-m3" is installed as "bge-m3:latest"
    return any(m == required or m.split(":")[0] == required for m in models)


@router.get("/health", response_model=Health)
def health(request: Request, conn=Depends(get_conn)) -> Health:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        db_ok = True
    except Exception:  # noqa: BLE001 - health must report, not raise
        db_ok = False
    try:
        models = request.app.state.ollama.tags()
        ollama_ok = True
    except Exception:  # noqa: BLE001
        models, ollama_ok = [], False
    required = request.app.state.required_models
    return Health(db=db_ok, ollama=ollama_ok, models=models,
                  missing_models=[m for m in required if not _installed(m, models)])
