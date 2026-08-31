from abc import ABC, abstractmethod

from .client import PostgresClient
from .repositories.base import SqlAlchemyRepository
from .repositories.order import OrderRepository
from .repositories.waste import WasteRepository


class AbstractUnitOfWork(ABC):
    """https://www.cosmicpython.com/book/chapter_06_uow.html

    Usage:
        async with uow:
            waste = await uow.waste.fetch_one({"external_id": "abc"})
            await uow.waste.update({"id": waste["id"]}, {"status": "done"})
        # commit() on clean exit, rollback() if an exception propagated
    """

    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: BaseException, exc_tb: object
    ) -> None:
        if exc_val:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...


def _repository_fields(cls: type) -> dict[str, type[SqlAlchemyRepository]]:
    """Collects repository classes declared as class attributes across the
    whole MRO (subclass attributes win over base-class ones with the same
    name), e.g. `waste = WasteRepository` on a SqlAlchemyUnitOfWork subclass.
    """
    fields: dict[str, type[SqlAlchemyRepository]] = {}
    for klass in reversed(cls.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, type) and issubclass(value, SqlAlchemyRepository):
                fields[name] = value
    return fields


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """Subclass and declare repository classes as plain class attributes —
    no need to override __aenter__ or wire anything by hand:

        class DemoUnitOfWork(SqlAlchemyUnitOfWork):
            waste = WasteRepository
            order = OrderRepository

        async with DemoUnitOfWork() as uow:
            await uow.waste.insert(...)   # uow.order is available too,
                                           # same session/transaction
    """

    def __init__(self) -> None:
        self.client = PostgresClient()

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        if self.client.sessionmaker is None:
            await self.client.connect()
        await self.client.open()
        for name, repo_cls in _repository_fields(type(self)).items():
            repo = repo_cls()
            repo.client = self.client  # share this UoW's session/transaction
            setattr(self, name, repo)
        return await super().__aenter__()  # type: ignore[return-value]

    async def __aexit__(
        self, exc_type: type, exc_val: BaseException, exc_tb: object
    ) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        await self.client.close_session()

    async def commit(self) -> None:
        await self.client.commit()

    async def rollback(self) -> None:
        await self.client.rollback()


class DemoUnitOfWork(SqlAlchemyUnitOfWork):
    """Concrete UoW for this demo: waste + order, sharing one transaction."""

    waste = WasteRepository
    order = OrderRepository
