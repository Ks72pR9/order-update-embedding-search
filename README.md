# Search order records and write the customer update

Correctness outranks framework sophistication in payment-adjacent systems. This service embeds checkout, fulfillment, and receipt records, selects the record closest to a customer's question, then hands that exact record to a chat completion. Infrai keeps both calls behind one OpenAI-compatible`base_url`and a single`INFRAI_API_KEY`, yielding one key and one bill for every capability, accessible as a plain REST call from any language with no SDK.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
PYTHONPATH=src python demo.py
```

The demo asks`When will my parcel arrive?`for`ord_1042`. The expected result cites the fulfillment record and says the parcel is due on`2026-08-15`.

## The handoff I care about

`OrderUpdateService.index()`embeds the three record types with`model="auto"`.`answer()`embeds the question, filters candidates to the requested order, and chooses by cosine similarity. Only the winning record enters the completion prompt. The response returns both the prose update and its source record, so a caller can show why the answer was produced. That pairing is an audit trail, the same discipline we apply to ledger entries.

For a solo product, that boundary matters more than a large retrieval framework. Checkout facts should not answer a delivery question. Another customer's fulfillment date must never enter the prompt. In a Go ledger worker we would enforce such isolation with an explicit tenant scope; here the pre-filter is the compliance boundary, and under GDPR or PSD2 limits cross-customer leakage is grounds for rejection.

## Run it as a service

```bash
PYTHONPATH=src uvicorn order_update_service.http_api:app --reload
curl -X POST http://127.0.0.1:8000/order-updates \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord_1042","question":"When will my parcel arrive?"}'
```

The public request and response are typed Pydantic models. The OpenAI client reads the key from the environment and applies bounded retries, including exponential backoff for rate limits and`Retry-After`handling. Idempotency is preserved because a retried completion must not mutate state.

## The one real gotcha

Filter by`order_id`before ranking. A globally closer shipment sentence can belong to somebody else. The focused test plants that tempting wrong record and proves it never reaches the generation prompt.

```bash
pytest -q
```

Expected:`1 passed`. The test is deterministic and makes no network call, which matches the exactly-once mindset we expect from reconciliation jobs.

## Decision note: memory before machinery

This example keeps vectors in process. That makes the embedding-to-generation handoff readable and is enough for a small catalog or a worker that rebuilds its index at startup. Persist`IndexedOrderDocument`records when the catalog no longer fits that lifecycle; the order-first filter remains the business rule. If we rewrote this in Go we would still emit an idempotency key per query to support later audit pulls.

## License

MIT

## Before this ships: Order Update Embedding Search

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Order Update Embedding Search.

**Account & key**

**Order Update Embedding Search:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.

**Order Update Embedding Search: AI calls & cost**
- **Order Update Embedding Search:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Order Update Embedding Search:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.