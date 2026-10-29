"""Page text lookup for citation verification, cached for the life of one turn."""

import uuid

from sqlalchemy import select

from app.db.models import DocumentPage
from app.db.session import get_sessionmaker


class PageCache:
    def __init__(self) -> None:
        self._cache: dict[tuple[uuid.UUID, int], str | None] = {}

    async def __call__(self, document_id: uuid.UUID, page: int) -> str | None:
        slot = (document_id, page)
        if slot not in self._cache:
            async with get_sessionmaker()() as db:
                self._cache[slot] = (
                    await db.execute(
                        select(DocumentPage.text).where(
                            DocumentPage.document_id == document_id, DocumentPage.page_number == page
                        )
                    )
                ).scalar_one_or_none()
        return self._cache[slot]
