# Ledger Indexer — Releases

## v2.0.0

**Release date: 2026-03-11**

The 2.0 line is now generally available. This release finalises the streaming
ingest rewrite and the new query planner.

### Highlights

- Streaming ingest replaces the batch loader.
- Query planner rewritten around the block-height index.
- Breaking: the `/v1/blocks` endpoint is removed. Use `/v2/blocks`.

### Previous releases

| Version | Date |
| --- | --- |
| v1.9.2 | 2026-01-28 |
| v1.9.1 | 2025-12-04 |
