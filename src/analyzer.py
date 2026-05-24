"""Compute adoption metrics from a stream of keyed-nonce transactions."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .data_models import AdoptionMetrics, KeyedNonceTransaction

# Rough storage estimate per NONCE_MANAGER slot.
# 32 bytes key + 32 bytes value (packed seq + flags) + storage overhead.
NONCE_MANAGER_BYTES_PER_SLOT = 96


def aggregate(txs: Iterable[KeyedNonceTransaction]) -> AdoptionMetrics:
    """Aggregate a list of transactions into adoption metrics.

    Single-pass O(n) over the input. Suitable for live streaming windows or
    historical batch reanalysis.
    """
    tx_list = list(txs)
    if not tx_list:
        return AdoptionMetrics(
            window_start_block=0,
            window_end_block=0,
            total_txs=0,
            legacy_txs=0,
            keyed_txs=0,
            first_use_count=0,
            unique_senders=0,
            senders_using_keyed=0,
            nonce_manager_storage_bytes=0,
            max_seq_observed=0,
            avg_keys_per_keyed_sender=0.0,
        )

    blocks = [t.block_number for t in tx_list]
    legacy = sum(1 for t in tx_list if t.is_legacy)
    keyed = sum(1 for t in tx_list if t.is_keyed)
    first_use = sum(1 for t in tx_list if t.is_first_use)
    senders = {t.sender for t in tx_list}
    keyed_senders = {t.sender for t in tx_list if t.is_keyed}
    max_seq = max((t.nonce_seq for t in tx_list if t.is_keyed), default=0)

    # Count distinct keys per keyed sender
    keys_per_sender: dict[str, set[int]] = defaultdict(set)
    for t in tx_list:
        if t.is_keyed:
            keys_per_sender[t.sender].add(t.nonce_key)
    if keyed_senders:
        total_keys = sum(len(s) for s in keys_per_sender.values())
        avg_keys = total_keys / len(keyed_senders)
    else:
        avg_keys = 0.0

    # Storage growth = number of distinct (sender, key) first uses observed
    storage_bytes = first_use * NONCE_MANAGER_BYTES_PER_SLOT

    return AdoptionMetrics(
        window_start_block=min(blocks),
        window_end_block=max(blocks),
        total_txs=len(tx_list),
        legacy_txs=legacy,
        keyed_txs=keyed,
        first_use_count=first_use,
        unique_senders=len(senders),
        senders_using_keyed=len(keyed_senders),
        nonce_manager_storage_bytes=storage_bytes,
        max_seq_observed=max_seq,
        avg_keys_per_keyed_sender=avg_keys,
    )


def bucket_by_block(
    txs: Iterable[KeyedNonceTransaction],
    bucket_size: int = 100,
) -> list[AdoptionMetrics]:
    """Bucket transactions by `bucket_size` blocks and aggregate each bucket.

    Useful for time-series visualization: each returned metric represents one
    bucket's adoption snapshot.
    """
    buckets: dict[int, list[KeyedNonceTransaction]] = defaultdict(list)
    for t in txs:
        bucket = t.block_number // bucket_size
        buckets[bucket].append(t)
    return [aggregate(buckets[k]) for k in sorted(buckets)]
