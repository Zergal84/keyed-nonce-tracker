# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Phase 2: live JSON-RPC integration plus Glamsterdam testnet validation.
- Phase 3: historical backfill into a public Parquet bucket.
- Phase 4: hosted Streamlit deployment, Grafana data-source plugin, Dune query template.

## [0.1.0] - 2026-05-24

Initial Phase 1 POC release.

### Added

- `KeyedNonceTransaction` and `AdoptionMetrics` dataclasses with EIP-8250
  constants (`KEYED_NONCE_FIRST_USE_GAS`, `MAX_NONCE_SEQ`).
- `KeyedNonceSimulator`: deterministic synthetic transaction stream generator
  with realistic sender adoption profiles, monotonic per-key sequences, and
  first-use marker accounting.
- `aggregate()` and `bucket_by_block()` analyzer functions, single-pass O(n)
  over the input stream.
- `EthRpcClient`: async JSON-RPC client with forward-compatible mapping from
  RPC transaction objects to the internal `KeyedNonceTransaction` model.
- Streamlit dashboard with simulator and live modes, sidebar controls, and
  Plotly time-series charts.
- 20 unit tests covering the analyzer, simulator, and RPC client. 100% line
  coverage on all non-UI modules.
- Ruff and mypy strict configuration; both pass on commit.
- GitHub Actions CI matrix on Python 3.10 through 3.13.

### Known limitations

- The dashboard's live-mode tab is stubbed pending availability of a
  Glamsterdam-aware testnet. The `EthRpcClient` itself is fully functional;
  it just is not yet wired into the Streamlit data-load callback.
- EIP-8250 spec field names (`nonceKey`, `nonceSeq`, `isKeyedNonceFirstUse`)
  are placeholder guesses. The mapping in `src/rpc_client.py` will be updated
  to match the finalized spec.
