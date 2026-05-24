"""Simulator for keyed-nonce transactions, used pre-Glamsterdam-activation.

The simulator generates synthetic but realistic transaction streams that exercise
the analyzer the same way live mainnet data would after EIP-8250 activates.

Realism heuristics:
- ~60% of senders never adopt keyed nonces (long-tail of legacy contracts/EOAs)
- ~25% adopt 1-2 keys (typical smart wallet / privacy protocol pattern)
- ~15% adopt 5+ keys (intent settlement layers, MEV bots)
- First-use fraction tapers off over time as keys accumulate
- Block size ~150 txs (current mainnet ballpark)
"""
from __future__ import annotations

import hashlib
import random
import time
from collections import defaultdict
from collections.abc import Iterator

from .data_models import KeyedNonceTransaction


def _fake_addr(seed: int) -> str:
    """Generate a deterministic synthetic Ethereum address from a seed."""
    h = hashlib.sha256(f"sender:{seed}".encode()).hexdigest()
    return "0x" + h[:40]


def _fake_tx_hash(block_number: int, tx_index: int) -> str:
    h = hashlib.sha256(f"tx:{block_number}:{tx_index}".encode()).hexdigest()
    return "0x" + h


class KeyedNonceSimulator:
    """Stateful simulator that produces realistic keyed-nonce tx streams.

    State tracks per-sender adoption profile and per-(sender, key) sequence
    counter, so generated transactions have valid (monotonic) seq numbers
    within their key.
    """

    def __init__(
        self,
        num_senders: int = 5000,
        rng_seed: int = 42,
        block_size_avg: int = 150,
    ) -> None:
        self._rng = random.Random(rng_seed)
        self._num_senders = num_senders
        self._block_size_avg = block_size_avg
        # Assign adoption profile per sender
        # 60% legacy-only, 25% low-keyed (1-2 keys), 15% high-keyed (5+ keys)
        self._adoption: dict[int, list[int]] = {}
        for i in range(num_senders):
            r = self._rng.random()
            if r < 0.60:
                self._adoption[i] = [0]  # legacy only
            elif r < 0.85:
                num_keys = self._rng.randint(1, 2)
                self._adoption[i] = [0] + [self._rng.randint(1, 100) for _ in range(num_keys)]
            else:
                num_keys = self._rng.randint(5, 12)
                self._adoption[i] = [0] + [self._rng.randint(1, 10_000) for _ in range(num_keys)]
        # Per-(sender, key) seq counter
        self._seq_state: dict[tuple[int, int], int] = defaultdict(int)
        # Per-(sender, key) first-use marker
        self._first_use_done: set[tuple[int, int]] = set()

    def stream_blocks(
        self,
        start_block: int,
        num_blocks: int,
        start_time: int | None = None,
    ) -> Iterator[KeyedNonceTransaction]:
        """Yield simulated transactions across `num_blocks` blocks."""
        ts = start_time if start_time is not None else int(time.time())
        block_time = 12  # seconds per Ethereum slot post-merge

        for block_offset in range(num_blocks):
            block_number = start_block + block_offset
            block_ts = ts + (block_offset * block_time)
            # Variable block size around average
            n_txs = max(1, int(self._rng.gauss(self._block_size_avg, 25)))
            for tx_idx in range(n_txs):
                sender_idx = self._rng.randint(0, self._num_senders - 1)
                key_choices = self._adoption[sender_idx]
                # Senders with keyed keys use them ~70% of the time after first use
                if len(key_choices) > 1 and self._rng.random() < 0.70:
                    nonce_key = self._rng.choice(key_choices[1:])
                else:
                    nonce_key = 0  # legacy

                state_key = (sender_idx, nonce_key)
                seq = self._seq_state[state_key]
                self._seq_state[state_key] = seq + 1

                is_first_use = nonce_key != 0 and state_key not in self._first_use_done
                if is_first_use:
                    self._first_use_done.add(state_key)
                base_gas = self._rng.randint(21_000, 250_000)
                gas_used = base_gas + (20_000 if is_first_use else 0)

                yield KeyedNonceTransaction(
                    block_number=block_number,
                    tx_hash=_fake_tx_hash(block_number, tx_idx),
                    sender=_fake_addr(sender_idx),
                    nonce_key=nonce_key,
                    nonce_seq=seq,
                    gas_used=gas_used,
                    is_first_use=is_first_use,
                    timestamp=block_ts,
                )
