import uuid
from typing import Any

from ..models.order import Order
from .base import SqlAlchemyRepository


class OrderRepository(SqlAlchemyRepository[Order]):
    model = Order

    async def fetch_by_waste_id(self, waste_id: uuid.UUID) -> list[dict[str, Any]]:
        return await self.fetch_all({"waste_id": waste_id})
