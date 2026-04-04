# TODO

## Critical Before Production

- Expire stale `pending` orders and restore reserved ticket inventory.
- Add an `expires_at` flow for unpaid orders so abandoned checkouts do not hold stock indefinitely.
- Implement a cleanup path for expired reservations, either via a background job or an explicit reconciliation process.
