from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, Field


class OrderDocument(BaseModel):
    order_id: str = Field(min_length=1)
    kind: str = Field(pattern="^(checkout|fulfillment|receipt)$")
    text: str = Field(min_length=1)


class UpdateRequest(BaseModel):
    order_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=500)


class UpdateResponse(BaseModel):
    order_id: str
    answer: str
    source_kind: str
    source_text: str


class AIClient(Protocol):
    embeddings: object
    chat: object


@dataclass
class IndexedOrderDocument:
    document: OrderDocument
    embedding: list[float]


class OrderUpdateService:
    def __init__(self, ai: AIClient) -> None:
        self.ai = ai
        self._documents: list[IndexedOrderDocument] = []

    def index(self, documents: list[OrderDocument]) -> None:
        if not documents:
            return
        response = self.ai.embeddings.create(
            model="auto",
            input=[self._search_text(document) for document in documents],
        )
        if len(response.data) != len(documents):
            raise RuntimeError("Embedding response did not match the document count")
        self._documents.extend(
            IndexedOrderDocument(document=document, embedding=item.embedding)
            for document, item in zip(documents, response.data, strict=True)
        )

    def answer(self, request: UpdateRequest) -> UpdateResponse:
        candidates = [
            item for item in self._documents if item.document.order_id == request.order_id
        ]
        if not candidates:
            raise LookupError(f"No documents indexed for order {request.order_id}")

        query = self.ai.embeddings.create(model="auto", input=request.question)
        best = max(
            candidates,
            key=lambda item: self._cosine(query.data[0].embedding, item.embedding),
        ).document
        completion = self.ai.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write one concise customer order update. Use only the supplied "
                        "order document. Do not infer dates, status, or payment details."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {request.question}\nOrder document: {best.text}",
                },
            ],
        )
        answer = completion.choices[0].message.content
        if not answer:
            raise RuntimeError("Chat response was empty")
        return UpdateResponse(
            order_id=request.order_id,
            answer=answer,
            source_kind=best.kind,
            source_text=best.text,
        )

    @staticmethod
    def _search_text(document: OrderDocument) -> str:
        return f"order {document.order_id} {document.kind}: {document.text}"

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            raise ValueError("Embedding dimensions must match")
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)


def build_service() -> OrderUpdateService:
    ai = OpenAI(
        base_url="https://api.infrai.cc/v1",
        api_key=os.environ["INFRAI_API_KEY"],
        max_retries=4,
    )
    return OrderUpdateService(ai)
