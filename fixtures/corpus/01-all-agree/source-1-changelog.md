# Changelog

All notable changes to Ledger Indexer are recorded here.

## [2.0.0] — 2026-03-11

### Added
- Streaming ingest pipeline.
- Block-height index used by the new query planner.

### Removed
- The deprecated `/v1/blocks` endpoint.

## [1.9.2] — 2026-01-28

### Fixed
- Reconnect loop when the upstream node restarts.
