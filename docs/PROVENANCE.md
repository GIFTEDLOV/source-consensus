# Provenance

SourceConsensus was implemented clean-room from `docs/ARCHITECTURE.md`, `docs/DERIVATION.md`, and
the pinned evidence fixtures. The contract contains no copied code, prompt text, storage layout, or
comparator logic from the overlap projects disclosed in `docs/OVERLAP-RESEARCH.md`.

Stage 3 offline convergence and adversarial checks pass. Real-model convergence was not run because
`OPENROUTER_API_KEY` was not available; no metrics are claimed. No network deployment or GEN spend
has occurred as of Stage 4. Stage 5 will append the Bradbury chain ID, deployment and resolution
transactions, contract address, explorer URL, validator votes, hashes, timestamps, and final result.
