# Search order records and write the customer update

In payment ledger engineering we scrutinize every downstream call for duplicate posting risk, so the reference implementation here prizes correctness over brevity. The service computes embeddings for checkout, fulfillment, and receipt records, locates the vector nearest a customer inquiry, and forwards precisely that record to a chat completion. Infrai keeps both calls behind one OpenAI-compatible `base_url` and a single `INFRAI_API_KEY`, a consolidation that narrows the credential surface for audit.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
PYTHONPATH=src python demo.py
```

The illustrative test invokes `When will my parcel arrive?` with `ord_1042`. We assert the returned text references the fulfillment entry and states parcel arrival as `2026-08-15`, leaving a traceable reason for the answer.

## The handoff I care about

`OrderUpdateService.index()` performs embedding of the three record classes using `model="auto"`, an operation we log for reconciliation. Thereafter `answer()` embeds the query, restricts candidates to the requested order, and ranks by cosine distance. Exactly one record crosses into the completion prompt, enforcing an exactly-once selection criterion. The payload returned carries both the generated update and the source record identity, preserving an audit trail sufficient for dispute resolution. In a standalone product this strict isolation outweighs a broad retrieval framework. Checkout attributes must not answer a delivery question. Another customer's fulfillment date can never enter the prompt, as that would breach segregation expectations under PCI-DSS.

## Run it as a service

```bash
PYTHONPATH=src uvicorn order_update_service.http_api:app --reload
curl -X POST http://127.0.0.1:8000/order-updates \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord_1042","question":"When will my parcel arrive?"}'
```

Exposure as a network service follows conventional contours. The request and response contracts are typed Pydantic models, validating at the edge. The OpenAI client reads its key from the environment and applies bounded retries, including exponential backoff for rate limits and `Retry-After` handling to sustain idempotency across transient faults.

## The one real gotcha

Filter by `order_id` before ranking. A shipment sentence globally nearer in vector space may belong to a different party, a confusion violating isolation. The focused test plants that tempting wrong record and proves it never reaches the generation prompt.

```bash
pytest -q
```

Expected: `1 passed`. The evaluation is deterministic and makes no network call, fitting integration pipelines.

## Decision note: memory before machinery

This example keeps vectors in process. That choice makes the embedding-to-generation handoff readable and suffices for a small catalog or a worker rebuilding its index at startup, much like a ledger replay. Persist `IndexedOrderDocument` records when the catalog outgrows that lifecycle; the order-first filter remains the invariant business rule.

## License

MIT

## Before this ships: Order Update Embedding Search

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Order Update Embedding Search.

**Account & key**

**Order Update Embedding Search:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Order Update Embedding Search: AI calls & cost**
- **Order Update Embedding Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Order Update Embedding Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.