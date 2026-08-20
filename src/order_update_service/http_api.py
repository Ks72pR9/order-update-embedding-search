from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .order_updates import (
    OrderDocument,
    OrderUpdateService,
    UpdateRequest,
    UpdateResponse,
    build_service,
)


SEED_DOCUMENTS = [
    OrderDocument(
        order_id="ord_1042",
        kind="checkout",
        text="Checkout completed with card payment on 2026-08-12.",
    ),
    OrderDocument(
        order_id="ord_1042",
        kind="fulfillment",
        text="Parcel left the warehouse on 2026-08-13 and is due on 2026-08-15.",
    ),
    OrderDocument(
        order_id="ord_1042",
        kind="receipt",
        text="Receipt R-1042 was issued for the completed card payment.",
    ),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = build_service()
    service.index(SEED_DOCUMENTS)
    app.state.order_updates = service
    yield


app = FastAPI(title="Order update search", lifespan=lifespan)


@app.post("/order-updates", response_model=UpdateResponse)
def create_order_update(request: UpdateRequest) -> UpdateResponse:
    service: OrderUpdateService = app.state.order_updates
    try:
        return service.answer(request)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

