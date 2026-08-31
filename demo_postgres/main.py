from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException

from .client import PostgresClient
from .repositories.waste import WasteRepository
from .unit_of_work import DemoUnitOfWork


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await PostgresClient.connect()
    yield
    await PostgresClient.close()


app = FastAPI(lifespan=lifespan)


@app.get("/waste")
async def list_waste() -> list[dict[str, Any]]:
    async with DemoUnitOfWork() as uow:
        return await uow.waste.fetch_all()


@app.get("/waste/{external_id}/raw")
async def read_waste_raw(external_id: str) -> dict[str, Any]:
    """Same lookup as GET /waste/{external_id}, but WasteRepository is used
    directly — no UoW involved, it manages its own client/session for this
    one call."""
    repo = WasteRepository()
    waste = await repo.fetch_by_external_id(external_id)
    if waste is None:
        raise HTTPException(status_code=404, detail="waste not found")
    return waste


@app.post("/waste")
async def create_waste(external_id: str) -> dict[str, Any]:
    async with DemoUnitOfWork() as uow:
        return await uow.waste.insert({"external_id": external_id})


@app.get("/waste/{external_id}")
async def read_waste(external_id: str) -> dict[str, Any]:
    async with DemoUnitOfWork() as uow:
        waste = await uow.waste.fetch_by_external_id(external_id)
    if waste is None:
        raise HTTPException(status_code=404, detail="waste not found")
    return waste


@app.post("/waste/{external_id}/orders")
async def create_order(external_id: str, amount: float) -> dict[str, Any]:
    async with DemoUnitOfWork() as uow:
        waste = await uow.waste.fetch_by_external_id(external_id)
        if waste is None:
            raise HTTPException(status_code=404, detail="waste not found")
        # both repositories share the same session/transaction here
        return await uow.order.insert({"waste_id": waste["id"], "amount": amount})