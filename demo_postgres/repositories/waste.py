from typing import Any, Optional

from ..models.waste import Waste
from .base import SqlAlchemyRepository


class WasteRepository(SqlAlchemyRepository[Waste]):
    model = Waste

    async def fetch_by_external_id(self, external_id: str) -> Optional[dict[str, Any]]:
        return await self.fetch_one({"external_id": external_id})
