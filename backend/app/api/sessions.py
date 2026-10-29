"""Session creation. Full session state (Redis with Postgres fallback) arrives with WS1-22."""

from fastapi import APIRouter, Response

from app.api.deps import SESSION_COOKIE, DbSession
from app.config import get_settings
from app.db.models import Session

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session(response: Response, db: DbSession) -> dict[str, str]:
    session = Session()
    db.add(session)
    await db.commit()
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        str(session.id),
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=settings.session_ttl_seconds,
    )
    return {"session_id": str(session.id)}
