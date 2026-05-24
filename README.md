# Keyed Nonce Adoption Tracker

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

A Python dashboard for tracking EIP-8250 keyed-nonce adoption on Ethereum mainnet once the Glamsterdam upgrade activates the new transaction-nonce format.

## What is EIP-8250?

EIP-8250 replaces the linear nonce on frame transactions with a `(nonce_key, nonce_seq)` pair. Transactions on different non-zero keys are replay-independent, so a single sender address can run several parallel nonce streams. The main beneficiaries are privacy protocols, smart wallets, and intent settlement infrastructure, where the current linear-nonce model creates head-of-line blocking: one stuck transaction blocks every later transaction from the same sender.

Spec: https://eips.ethereum.org/EIPS/eip-8250

## What this tool does

Once Glamsterdam ships, the tracker reads mainnet blocks via JSON-RPC and computes:

- adoption rate per block and per day, both transaction-level and sender-level
- `NONCE_MANAGER` storage growth, with slot allocations gated by `KEYED_NONCE_FIRST_USE_GAS = 20000`
- estimated throughput uplift for shared senders that actually use parallel keys
- per-key sequence distance from `MAX_NONCE_SEQ = 2**64 - 1` (key-exhaustion monitor)
- shared-sender usage patterns consistent with privacy protocols or intent settlement

Before Glamsterdam activates, the same code paths run against a synthetic data generator instead of mainnet.

## Architecture

```
JSON-RPC client (live mainnet OR simulator)
        |
        v
Transaction parser  ->  Analyzer (metrics)
                              |
                              v
                       Streamlit dashboard
```

The simulator and the live client both produce `KeyedNonceTransaction` objects with the same shape, so everything downstream is data-source agnostic. When Glamsterdam ships and the new fields land on RPC, only one mapping function in `src/rpc_client.py` needs to flip over.

## Quickstart

```bash
pip install -e .
streamlit run src/dashboard.py
```

The dashboard opens at `http://localhost:8501`. Use the sidebar to switch between simulator mode (default) and live mode (set the `RPC_URL` env var to a Glamsterdam-aware node).

## Roadmap

| Phase | Description | Status |
|---|---|---|
| 1 | Simulator, analyzer, dashboard, 10 unit tests | done |
| 2 | Live RPC client wired into the dashboard | stubbed, waits on a Glamsterdam testnet |
| 3 | Historical backfill from Glamsterdam genesis into Parquet | planned |
| 4 | Hosted dashboard, Grafana panel, Dune query template | planned |

## License

Apache-2.0. See [LICENSE](LICENSE).

## Notes

EIP-8250 is still a draft. Some of the constants and field names may shift during Glamsterdam scoping, and the EIP itself may or may not be included in the final scope. If the spec changes, the parser in `src/rpc_client.py` is the one place that needs updating.
