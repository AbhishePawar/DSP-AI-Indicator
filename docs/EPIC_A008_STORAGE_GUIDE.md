# EPIC-A008 — Storage Guide

## Default provider

`InMemoryStorageProvider` (`provider_id=in_memory`) — process-local.

## Port

Implement `StorageProviderPort`:

- `put` / `get` / `delete` / `list_keys` / `clear`
- `snapshot_state` / `restore_state` (for transactions)

Future providers can be swapped at registry construction without changing
repository or service APIs.
