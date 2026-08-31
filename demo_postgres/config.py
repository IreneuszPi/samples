import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class PostgresSettings:
    """Connection settings for :class:`demo_postgres.client.PostgresClient`.

    Mirrors the shape of the original ``postgres_settings.settings`` object
    (``USE_SSL`` + ``POSTGRES_CONNECTION_STRING``) so ``PostgresClient.connect``
    can stay untouched.
    """

    POSTGRES_CONNECTION_STRING: str = os.environ.get(
        "POSTGRES_CONNECTION_STRING",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
    )
    USE_SSL: bool = _env_bool("USE_SSL", False)


settings = PostgresSettings()