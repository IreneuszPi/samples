import os
import ssl
from typing import Any, ClassVar, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings


class PostgresClient:
    """Engine/sessionmaker are process-wide, shared by every instance as
    class attributes — set once via ``connect()`` (driven by the FastAPI
    lifespan, see main.py), torn down once via ``close()``. Session is
    per-instance, opened lazily via ``async with client:`` (or
    ``open()``/``close_session()`` directly).

    A session isn't safe to share across concurrent requests, so plain
    ``PostgresClient()`` — not a shared instance — is how every
    request/UoW/repository gets its own:

        async with PostgresClient() as client:
            repo = WasteRepository(client)
            await repo.fetch_all()

    ``connect()`` is copied verbatim from the original PostgresClient —
    its logic must not change.
    """

    engine: ClassVar[Optional[AsyncEngine]] = None
    sessionmaker: ClassVar[Optional[async_sessionmaker[AsyncSession]]] = None

    def __init__(self) -> None:
        self.settings = settings
        self.session: Optional[AsyncSession] = None

    @classmethod
    async def connect(cls) -> None:
        connect_args = {}
        if settings.USE_SSL:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = os.environ["SSL_CHECK_HOSTNAME"] == "True"
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.load_verify_locations(cafile=os.environ["SSL_ROOT_CERTIFICATE"])
            ssl_context.load_cert_chain(
                certfile=os.environ["SSL_CERTIFICATE"],
                keyfile=os.environ["SSL_PRIVATE_KEY"],
            )
            connect_args["ssl"] = ssl_context
        cls.engine = create_async_engine(
            settings.POSTGRES_CONNECTION_STRING,
            connect_args=connect_args,  # type: ignore
            echo=True,
        )

        cls.sessionmaker = async_sessionmaker(
            cls.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @classmethod
    async def close(cls) -> None:
        if cls.engine:
            await cls.engine.dispose()

    async def open(self) -> "PostgresClient":
        assert self.sessionmaker is not None  # mypy — call connect() first
        self.session = self.sessionmaker()
        return self

    async def close_session(self) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def __aenter__(self) -> "PostgresClient":
        return await self.open()

    async def __aexit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
        await self.close_session()

    async def commit(self) -> None:
        assert self.session is not None  # mypy — call open() first
        await self.session.commit()

    async def rollback(self) -> None:
        assert self.session is not None  # mypy — call open() first
        await self.session.rollback()

    async def execute(self, stmt: Any) -> Any:
        """Run a statement on the current session — or, if none is open
        (no surrounding UnitOfWork/``async with``), open one just for this
        statement, commit it, and close it again."""
        if self.session is not None:
            return await self.session.execute(stmt)
        async with self:
            result = await self.session.execute(stmt)  # type: ignore[union-attr]
            await self.commit()
            return result