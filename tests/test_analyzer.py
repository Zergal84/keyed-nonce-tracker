"""Unit tests for the analyzer."""
from __future__ import annotations

from src.analyzer import aggregate, bucket_by_block
from src.data_models import KeyedNonceTransaction


def _tx(
    block: int = 100,
    sender: str = "0xAA",
    key: int = 0,
    seq: int = 0,
    gas: int = 21000,
    first_use: bool = False,
    ts: int = 1_700_000_000,
) -> KeyedNonceTransaction:
    return KeyedNonceTransaction(
        block_number=block,
        tx_hash=f"0x{block:064x}",
        sender=sender,
        nonce_key=key,
        nonce_seq=seq,
        gas_used=gas,
        is_first_use=first_use,
        timestamp=ts,
    )


def test_aggregate_empty():
    m = aggregate([])
    assert m.total_txs == 0
    assert m.adoption_rate == 0.0
    assert m.key_exhaustion_headroom == 1.0


def test_aggregate_legacy_only():
    txs = [_tx(sender=f"0x{i}", key=0, seq=i) for i in range(10)]
    m = aggregate(txs)
    assert m.total_txs == 10
    assert m.legacy_txs == 10
    assert m.keyed_txs == 0
    assert m.adoption_rate == 0.0
    assert m.sender_adoption_rate == 0.0
    assert m.first_use_count == 0
    assert m.nonce_manager_storage_bytes == 0


def test_aggregate_mixed():
    # 5 legacy, 5 keyed from 2 senders
    txs = [
        _tx(sender="0xAA", key=0, seq=0),
        _tx(sender="0xAA", key=0, seq=1),
        _tx(sender="0xAA", key=42, seq=0, first_use=True),
        _tx(sender="0xAA", key=42, seq=1),
        _tx(sender="0xBB", key=0, seq=0),
        _tx(sender="0xBB", key=0, seq=1),
        _tx(sender="0xBB", key=0, seq=2),
        _tx(sender="0xBB", key=7, seq=0, first_use=True),
        _tx(sender="0xBB", key=7, seq=1),
        _tx(sender="0xBB", key=99, seq=0, first_use=True),
    ]
    m = aggregate(txs)
    assert m.total_txs == 10
    assert m.legacy_txs == 5
    assert m.keyed_txs == 5
    assert m.unique_senders == 2
    assert m.senders_using_keyed == 2
    assert m.first_use_count == 3
    assert m.adoption_rate == 0.5
    assert m.sender_adoption_rate == 1.0
    # 3 distinct keyed slots * 96 bytes
    assert m.nonce_manager_storage_bytes == 3 * 96
    # avg keys per keyed sender: 0xAA has 1 key, 0xBB has 2 → mean = 1.5
    assert m.avg_keys_per_keyed_sender == 1.5


def test_bucket_by_block_partitions():
    txs = [
        _tx(block=100), _tx(block=101), _tx(block=110),
        _tx(block=200), _tx(block=205),
    ]
    series = bucket_by_block(txs, bucket_size=50)
    # Buckets: 100-149 (3 txs), 150-249 → actually 200-249 (2 txs)
    assert len(series) == 2
    assert series[0].total_txs == 3
    assert series[1].total_txs == 2


def test_key_exhaustion_headroom_with_high_seq():
    from src.data_models import MAX_NONCE_SEQ
    txs = [_tx(sender="0xAA", key=1, seq=MAX_NONCE_SEQ // 2)]
    m = aggregate(txs)
    # Headroom should be ~0.5
    assert 0.49 < m.key_exhaustion_headroom < 0.51
