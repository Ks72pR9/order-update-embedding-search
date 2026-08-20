from types import SimpleNamespace

from order_update_service.order_updates import (
    OrderDocument,
    OrderUpdateService,
    UpdateRequest,
)


class FakeEmbeddings:
    def create(self, *, model: str, input: str | list[str]):
        texts = [input] if isinstance(input, str) else input
        vectors = []
        for text in texts:
            vector = [1.0, 0.0] if "parcel" in text.lower() or "fulfillment" in text else [0.0, 1.0]
            vectors.append(SimpleNamespace(embedding=vector))
        return SimpleNamespace(data=vectors)


class FakeCompletions:
    def __init__(self) -> None:
        self.messages = []

    def create(self, *, model: str, messages: list[dict[str, str]]):
        self.messages = messages
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Your parcel is due on 2026-08-15."))]
        )


def test_customer_update_uses_the_matching_order_fulfillment_fact():
    completions = FakeCompletions()
    ai = SimpleNamespace(
        embeddings=FakeEmbeddings(),
        chat=SimpleNamespace(completions=completions),
    )
    service = OrderUpdateService(ai)
    service.index(
        [
            OrderDocument(order_id="ord_1042", kind="receipt", text="Receipt R-1042 was issued."),
            OrderDocument(
                order_id="ord_1042",
                kind="fulfillment",
                text="Parcel is due on 2026-08-15.",
            ),
            OrderDocument(
                order_id="ord_other",
                kind="fulfillment",
                text="Parcel is due on 2026-09-01.",
            ),
        ]
    )

    result = service.answer(
        UpdateRequest(order_id="ord_1042", question="When will my parcel arrive?")
    )

    assert result.source_kind == "fulfillment"
    assert result.source_text == "Parcel is due on 2026-08-15."
    assert "2026-09-01" not in completions.messages[1]["content"]

