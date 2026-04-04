# TODO

## Critical Before Production

- Expire stale `pending` orders and restore reserved ticket inventory.
- Add an `expires_at` flow for unpaid orders so abandoned checkouts do not hold stock indefinitely.
- Implement a cleanup path for expired reservations, either via a background job or an explicit reconciliation process.
- Add authentication and authorization for all `/api/admin/*` endpoints and protect the `/admin` frontend routes.
- Replace hardcoded local development URLs and credentials with environment-driven production configuration.
- Move backend and frontend containers off dev-mode commands like `--reload` and `vite dev`, and define a real production serving setup.
- Validate poster uploads for file type and size before writing them into the public static directory.
- Implement a real order lifecycle with payment confirmation, email delivery, and a server-side order confirmation lookup instead of relying on `sessionStorage`.
