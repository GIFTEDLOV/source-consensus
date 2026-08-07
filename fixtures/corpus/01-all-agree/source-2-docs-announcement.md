# Announcing Ledger Indexer 2.0

Ledger Indexer 2.0.0 was released on 11 March 2026.

Upgrading from the 1.9 line requires one migration step: the `/v1/blocks`
endpoint has been removed and callers must move to `/v2/blocks`. Everything
else is source-compatible.

The streaming ingest pipeline is the headline change. On our reference
workload it reduces catch-up time from roughly forty minutes to under six.
