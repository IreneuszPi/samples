from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import and_, delete, insert, select, update

from ..client import PostgresClient
from ..models.base import Base

T = TypeVar("T", bound=Base)


class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    async def fetch_all(
        self, filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def fetch_one(self, filters: dict[str, Any]) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    async def insert(self, values: dict[str, Any]) -> Any: ...

    @abstractmethod
    async def update(self, filters: dict[str, Any], values: dict[str, Any]) -> Any: ...

    @abstractmethod
    async def delete(self, filters: dict[str, Any]) -> Any: ...


class SqlAlchemyRepository(AbstractRepository[T]):
    """Generic per-model repository.

    Same query logic as before, but operating through a :class:`PostgresClient`
    it's handed rather than a raw session — the client owns the session, the
    repository just asks it to run statements. Concrete per-model
    repositories (see repositories/waste.py) subclass this and set ``model``.

    Handed a client (e.g. by a UnitOfWork), several calls on the repository
    share that one session/transaction — the caller owns opening/closing it
    and committing/rolling back. Used on its own with no client, each call
    opens its own session and commits it, since a standalone repository only
    ever does one thing at a time — see :meth:`PostgresClient.execute`:

        repo = WasteRepository()
        await repo.fetch_all()
    """

    model: type[T]

    def __init__(self) -> None:
        self.client = PostgresClient()

    async def execute(self, stmt: Any) -> Any:
        return await self.client.execute(stmt)

    async def fetch_all(
        self, filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        stmt = select(self.model)

        if filters:
            conditions = [self.model.__table__.c[k] == v for k, v in filters.items()]
            stmt = stmt.where(and_(*conditions))

        result = await self.execute(stmt)
        rows = result.scalars()
        return [r.as_dict() for r in rows]

    async def fetch_one(self, filters: dict[str, Any]) -> Optional[dict[str, Any]]:
        stmt = select(self.model)
        if filters:
            conditions = [self.model.__table__.c[k] == v for k, v in filters.items()]
            stmt = stmt.where(and_(*conditions))
        result = await self.execute(stmt)
        row = result.scalar_one_or_none()
        return row.as_dict() if row else None

    async def insert(self, values: dict[str, Any]) -> dict[str, Any]:
        stmt = insert(self.model).values(**values).returning(self.model)
        result = await self.execute(stmt)
        row = result.scalar_one()
        return row.as_dict()

    async def update(
        self, filters: dict[str, Any], values: dict[str, Any]
    ) -> dict[str, Any]:
        stmt = update(self.model).values(**values).returning(self.model)
        conditions = [self.model.__table__.c[k] == v for k, v in filters.items()]
        stmt = stmt.where(and_(*conditions))
        result = await self.execute(stmt)
        updated_row = result.scalar_one()
        return updated_row.as_dict()

    async def delete(self, filters: dict[str, Any]) -> Any:
        stmt = delete(self.model)
        conditions = [self.model.__table__.c[k] == v for k, v in filters.items()]
        stmt = stmt.where(and_(*conditions))
        await self.execute(stmt)
