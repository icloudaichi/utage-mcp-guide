# Final documentation consistency check

Snapshot: `utage-mcp-guide` commit `25aaf49`, 2026-10-03. Read-only review; no live calls, credentials, dependency installs, or repo edits. This private memo is outside the repository.

## Actionable contradictions

1. **P2 — pagination scope**: `docs/endpoint-testing.md:33` says without qualification that a list without `meta` never establishes completeness. `backup/SKILL.md:505` and the backup implementation accept the officially non-paginated steps/pages `data`-only schema. Limit the first claim to paginated endpoints and explicitly identify the endpoint-specific non-paginated exception.
2. **P2 — action creation guidance**: `backup/SKILL.md:533` unconditionally says actions cannot be created by API and require the management UI. `SKILL.md:128`, `messages/SKILL.md:22`, and the current catalog expose `funnel_action_create` / `message_action_create`. Clarify MCP resource-specific creation is exposed but restoration writes are untested; do not infer an unverified REST path or require the UI universally.

## Consistent items

- Catalog Markdown and JSON contain the same 253 names; operation/provider/live-status rows agree. Counts: 120 read, 133 write; all input schema fields remain `not_captured`.
- Successful catalog receipt references exist and point to `read_verified`; failed/non-JSON and Daichi auth observations remain separate. Every receipt fixture reference exists.
- The corrected `detail_id` successful read is described as argument observation, not complete JSON Schema capture. Payment configuration is distinguished from individual subscriptions, statuses, and next-charge dates.
- Daichi blocked auth, no fallback, no reauthentication, narrow live reads, historical dated observations, and offline/live limits are consistently stated.
- Backup docs match the UTF-8 ID SHA-256 64-hex suffix naming and per-step complete/incomplete status; real-service backup is explicitly unexecuted.

MAGI summary/final provenance assembly was intentionally excluded from missing-link findings. No other concrete factual contradiction identified.
