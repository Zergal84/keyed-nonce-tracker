# Contributing

Thanks for looking at this project. It is small and early; the most useful
contributions right now are bug reports, spec-revision tracking, and pull
requests against the RPC client when Glamsterdam testnet field names settle.

## Local setup

```bash
git clone https://github.com/Zergal84/keyed-nonce-tracker.git
cd keyed-nonce-tracker
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the suite

```bash
pytest tests/                           # all tests
pytest tests/ --cov=src                 # with coverage
ruff check src/ tests/                  # lint
mypy src/                               # type-check
streamlit run src/dashboard.py          # interactive dashboard
```

All three of the above (pytest, ruff, mypy) must be clean before a pull
request can land. CI runs them on Python 3.10, 3.11, 3.12, and 3.13.

## Code conventions

- Type annotations are required; mypy runs in strict mode.
- New modules add a one-paragraph docstring at the top describing what the
  module is for and how it fits into the architecture.
- New public functions and classes get a docstring.
- The simulator and the RPC client must always produce `KeyedNonceTransaction`
  objects with the same shape. If the spec changes the field names, update
  the mapping in `src/rpc_client.py` and the simulator together.

## Tests

Add a test for any new behavior. The existing tests are the template:

- `test_analyzer.py` exercises pure functions with hand-built fixtures.
- `test_simulator.py` exercises determinism, distribution shape, and invariants.
- `test_rpc_client.py` uses `aioresponses` to mock HTTP without a live node.

## Pull requests

- Keep PRs focused on one change. Small PRs land fast.
- Reference the relevant EIP number in the PR title if the change is
  spec-driven.
- Update `CHANGELOG.md` under `[Unreleased]` for any user-visible change.

## Reporting bugs

Open an issue with a minimal reproduction. If the bug is in the analyzer,
include the input transaction list (a few lines of synthetic data is fine).
If the bug is in the RPC client, include the upstream node's vendor and
version, the request, and the response.

## Spec revisions

EIP-8250 is still a draft. If you spot a discrepancy between this project
and the latest EIP-8250 revision, open an issue with the EIP commit hash
and the diff that needs to land.
