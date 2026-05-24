"""Performance benchmark for simulator and analyzer.

Run with: `python scripts/bench.py`

Reports:
- Simulator throughput (transactions per second of wall time)
- Analyzer throughput (aggregate() and bucket_by_block())
- Total round-trip on a representative workload (200 blocks, 5000 senders)

Numbers are reported with one round of warm-up, then averaged over three
runs. They give a rough sense of how the tool scales when fed real mainnet
volume; mainnet currently produces around 150 txs/block, so 200 blocks is
roughly 30k transactions, comparable to a 40-minute mainnet window.
"""
from __future__ import annotations

import time
from statistics import mean

from src.analyzer import aggregate, bucket_by_block
from src.simulator import KeyedNonceSimulator


def time_block(label: str, fn, *args, **kwargs) -> tuple[float, object]:
    runs: list[float] = []
    result = None
    # Warm-up run, discarded.
    fn(*args, **kwargs)
    for _ in range(3):
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        runs.append(time.perf_counter() - t0)
    avg = mean(runs)
    print(f"  {label:45s} {avg * 1000:7.2f} ms (avg of 3)")
    return avg, result


def main() -> None:
    print("Keyed Nonce Tracker - benchmark")
    print("Workload: 200 blocks, 5000 senders, block size avg 150 txs\n")

    sim_seconds, _ = time_block(
        "Simulator: generate 200 blocks",
        lambda: list(
            KeyedNonceSimulator(num_senders=5000, rng_seed=42).stream_blocks(
                start_block=23_000_000, num_blocks=200
            )
        ),
    )

    # Generate once outside the analyzer-timing loop.
    sim = KeyedNonceSimulator(num_senders=5000, rng_seed=42)
    txs = list(sim.stream_blocks(start_block=23_000_000, num_blocks=200))
    n = len(txs)
    print(f"\n  generated {n:,} transactions")

    agg_seconds, _ = time_block(
        f"Analyzer: aggregate({n:,} txs)", aggregate, txs
    )
    bucket_seconds, buckets = time_block(
        f"Analyzer: bucket_by_block({n:,} txs, bucket=50)",
        bucket_by_block,
        txs,
        50,
    )
    print(f"\n  produced {len(buckets)} time-series buckets")
    print(f"\n  simulator throughput: {n / sim_seconds / 1000:.1f}k txs/sec")
    print(f"  analyzer throughput:  {n / agg_seconds / 1_000_000:.2f}M txs/sec (aggregate)")
    print(
        f"  end-to-end: simulator + analyzer + bucket = "
        f"{(sim_seconds + agg_seconds + bucket_seconds) * 1000:.0f} ms total"
    )


if __name__ == "__main__":
    main()
