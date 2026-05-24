"""Unit tests for the simulator."""
from __future__ import annotations

from src.simulator import KeyedNonceSimulator


def test_simulator_produces_expected_volume():
    sim = KeyedNonceSimulator(num_senders=100, rng_seed=1, block_size_avg=20)
    txs = list(sim.stream_blocks(start_block=1000, num_blocks=10))
    # Approximately 10 * 20 = 200 txs, allow ±30% slack
    assert 140 <= len(txs) <= 260


def test_simulator_deterministic():
    sim1 = KeyedNonceSimulator(num_senders=100, rng_seed=42)
    sim2 = KeyedNonceSimulator(num_senders=100, rng_seed=42)
    txs1 = list(sim1.stream_blocks(start_block=1000, num_blocks=5))
    txs2 = list(sim2.stream_blocks(start_block=1000, num_blocks=5))
    assert [t.tx_hash for t in txs1] == [t.tx_hash for t in txs2]
    assert [t.sender for t in txs1] == [t.sender for t in txs2]


def test_simulator_has_both_legacy_and_keyed():
    sim = KeyedNonceSimulator(num_senders=200, rng_seed=7)
    txs = list(sim.stream_blocks(start_block=1000, num_blocks=20))
    legacy = sum(1 for t in txs if t.is_legacy)
    keyed = sum(1 for t in txs if t.is_keyed)
    assert legacy > 0
    assert keyed > 0


def test_simulator_seq_monotonic_per_key():
    sim = KeyedNonceSimulator(num_senders=50, rng_seed=11)
    txs = list(sim.stream_blocks(start_block=1000, num_blocks=10))
    # Group by (sender, key) and check seq is monotonically increasing (in order of emission)
    state: dict[tuple[str, int], int] = {}
    for t in txs:
        sk = (t.sender, t.nonce_key)
        if sk in state:
            assert t.nonce_seq == state[sk] + 1, f"Non-monotonic seq for {sk}"
        state[sk] = t.nonce_seq


def test_simulator_first_use_only_once_per_key():
    sim = KeyedNonceSimulator(num_senders=30, rng_seed=3)
    txs = list(sim.stream_blocks(start_block=1000, num_blocks=5))
    first_use_keys = [(t.sender, t.nonce_key) for t in txs if t.is_first_use]
    # Each (sender, key) should appear at most once as first_use
    assert len(first_use_keys) == len(set(first_use_keys))
