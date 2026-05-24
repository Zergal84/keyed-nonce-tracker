"""Pydantic models for keyed-nonce transactions and adoption metrics.

EIP-8250 introduces a keyed nonce system that replaces the linear single-nonce
field on frame transactions with a `(nonce_key, nonce_seq)` tuple. Transactions
on different non-zero keys are replay-independent.

Constants per EIP-8250 draft:
- KEYED_NONCE_FIRST_USE_GAS = 20000 (surcharge on first use of a new key)
- MAX_NONCE_SEQ = 2**64 - 1 (per-key sequence ceiling)
"""
from __future__ import annotations

from dataclasses import dataclass

KEYED_NONCE_FIRST_USE_GAS = 20000
MAX_NONCE_SEQ = (1 << 64) - 1


@dataclass(frozen=True)
class KeyedNonceTransaction:
    """Single frame transaction with keyed-nonce semantics.

    When `nonce_key == 0`, the transaction uses legacy linear-nonce semantics
    (backwards compatibility per EIP-8250).
    """

    block_number: int
    tx_hash: str
    sender: str
    nonce_key: int           # 0 = legacy linear nonce
    nonce_seq: int
    gas_used: int
    is_first_use: bool       # True if this tx allocated a new NONCE_MANAGER slot
    timestamp: int           # unix seconds

    @property
    def is_legacy(self) -> bool:
        """Legacy linear nonce (backwards-compatible mode)."""
        return self.nonce_key == 0

    @property
    def is_keyed(self) -> bool:
        """Uses the keyed-nonce scheme (non-zero key)."""
        return self.nonce_key != 0


@dataclass(frozen=True)
class AdoptionMetrics:
    """Aggregate adoption metrics across a window of transactions."""

    window_start_block: int
    window_end_block: int
    total_txs: int
    legacy_txs: int
    keyed_txs: int
    first_use_count: int                          # new keyed-nonce slot allocations
    unique_senders: int
    senders_using_keyed: int
    nonce_manager_storage_bytes: int              # cumulative storage growth estimate
    max_seq_observed: int                         # highest seq for any active key
    avg_keys_per_keyed_sender: float

    @property
    def adoption_rate(self) -> float:
        """Fraction of transactions using keyed-nonce scheme."""
        return self.keyed_txs / self.total_txs if self.total_txs else 0.0

    @property
    def sender_adoption_rate(self) -> float:
        """Fraction of unique senders that used at least one keyed nonce."""
        return self.senders_using_keyed / self.unique_senders if self.unique_senders else 0.0

    @property
    def key_exhaustion_headroom(self) -> float:
        """Fraction of MAX_NONCE_SEQ remaining for the busiest observed key.

        Returns 1.0 when no keyed activity, 0.0 when at ceiling.
        """
        if self.max_seq_observed == 0:
            return 1.0
        return max(0.0, 1.0 - (self.max_seq_observed / MAX_NONCE_SEQ))
