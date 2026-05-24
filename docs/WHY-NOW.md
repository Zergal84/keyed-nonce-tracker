# Why this matters now

Glamsterdam is currently scoped for H1 2026 activation. EIP-8250 is in
Draft Standards Track: Core status. If the EIP lands in the final scope,
the network gets a structurally different transaction-nonce model on
mainnet within months. There is no public tooling that aggregates how that
primitive actually gets used post-activation. The window to build that
tooling closes when mainnet ships.

## What changes the day Glamsterdam ships

The linear-nonce model has been the default since genesis. Every wallet,
every mempool implementation, every analytics tool assumes per-sender
linear ordering. Replacing it with `(nonce_key, nonce_seq)` has second-
order effects that the EIP authors and the All Core Devs discussion have
pre-modeled but cannot fully predict:

- **Privacy protocols** and smart wallets gain the ability to issue
  parallel transaction streams. Whether they actually use the new
  primitive, and at what pace, is empirical.

- **NONCE_MANAGER storage growth** is gated by a `KEYED_NONCE_FIRST_USE_GAS
  = 20000` surcharge. The surcharge is calibrated against expected usage.
  If actual usage exceeds the surcharge's damping effect, storage growth
  outpaces the design and follow-up mitigations may be needed.

- **Mempool implementations** must rewrite transaction selection logic to
  handle independent nonce domains. Mempool authors will benefit from
  empirical data on per-sender concurrency once it is observable.

- **Privacy-protocol fingerprints** become visible in keyed-nonce usage
  patterns. Mixers and intent-settlement layers that use shared sender
  addresses have a recognizable signature in keyed-nonce activity.

## What public tooling exists today

Etherscan and similar block explorers will eventually surface the new
fields per-transaction, but they are not designed to aggregate cross-
cutting protocol-level metrics for a single EIP.

Dune Analytics community spellbooks will eventually cover EIP-8250
patterns, but spellbook coverage typically lags activation by weeks to
months, and the depth depends on whether a motivated contributor writes
the queries.

Specialized post-fork analyses, like the EIP-1559 outcome studies
published after London, are typically one-shot research outputs without
continuous-monitoring infrastructure. They are valuable as historical
record but not as live operational dashboards.

The gap between these three is exactly what this project fills: a
continuously updated, EIP-specific analytics layer that produces shared
reference data the day Glamsterdam ships.

## The timing argument

A monitoring tool that ships **after** Glamsterdam mainnet activation
misses the most interesting data: the first weeks of adoption. Early
adoption patterns inform whether the gas surcharge holds, whether
expected adopters actually adopt, and whether mempool authors should
prioritize keyed-aware redesigns.

This project ships the simulator, analyzer, and dashboard now, so the
infrastructure is in place when Glamsterdam testnet exposes the new
fields. The work that remains is the JSON-RPC mapping update plus the
public dataset persistence layer. Both have known designs and known
estimates (3 + 4 weeks in the proposal). Neither requires waiting on
mainnet activation to begin.

## Where the work plugs into the All Core Devs process

The Magicians forum discussion threads for EIP-8141, EIP-8250, EIP-8266,
and EIP-7773 are the natural feedback channels. After grant decision, the
Phase 1 POC gets posted there with a request for sanity-check on the
analyzer's metric definitions. Substantive feedback from the threads
becomes Phase 2 priorities. The All Core Devs call notes channel is the
second touchpoint for mempool implementers who need the data once mainnet
activates.

## What this project is not

It is not a wallet, not an EIP-8250 implementation, not a node, not a
mempool. It is a single-purpose analytics tool that turns one new EIP's
post-activation data into a shared dashboard plus a public dataset. The
scope is deliberately narrow so the tool can ship reliably within the
proposed timeline.
