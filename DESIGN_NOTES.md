# Design Notes

## Authorization

Django remains the authorization boundary. Project-scoped endpoints resolve the authenticated user's `Membership` server-side, allow admin/member mutations where required, permit viewer reads where specified, and reject non-members; frontend visibility is only a usability aid.

## Append-only comments

Comments belong to a task and use the authenticated request user as author with a server-generated creation timestamp. The API exposes only collection `GET` and `POST`; it defines no comment update or delete route, preserving an append-only thread ordered oldest-first.

## Airtable idempotency

Each Airtable row stores the task's stable database UUID in `Task ID`. Before exporting, the server fetches existing Task IDs once, builds an in-memory mapping to Airtable record IDs, creates missing rows, and updates matching rows on subsequent exports.

## Airtable retries and error isolation

Writes are batched in groups of ten. Transient network failures and HTTP 429/500/502/503/504 responses receive at most three attempts with exponential backoff; permanent 400/401/403 responses are not retried, while record-specific batch failures fall back to isolated writes so one invalid record does not stop the remaining export.

Part 3a Task Comments was selected. Activity Feed was intentionally not implemented.
