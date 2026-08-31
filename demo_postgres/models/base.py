from typing import Any

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    ``as_dict`` is relied on by the generic repository (fetch_all/fetch_one/
    insert/update all return plain dicts, same as the original PostgresClient).
    """

    def as_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
