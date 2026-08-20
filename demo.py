from order_update_service.order_updates import UpdateRequest, build_service
from order_update_service.http_api import SEED_DOCUMENTS


service = build_service()
service.index(SEED_DOCUMENTS)
result = service.answer(
    UpdateRequest(order_id="ord_1042", question="When will my parcel arrive?")
)
print(result.model_dump_json(indent=2))

