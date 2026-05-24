"""Streamlit dashboard for keyed-nonce adoption metrics.

Run with: `streamlit run src/dashboard.py`

Modes:
- Simulator (default, pre-activation): synthetic data via KeyedNonceSimulator
- Live (post-activation): requires RPC_URL env var pointing to Glamsterdam-aware node
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from .analyzer import aggregate, bucket_by_block
from .data_models import MAX_NONCE_SEQ, NONCE_MANAGER_BYTES_PER_SLOT  # noqa: F401 (used in help text)
from .simulator import KeyedNonceSimulator


def _format_bytes(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


st.set_page_config(page_title="Keyed Nonce Adoption Tracker", layout="wide")

st.title("Keyed Nonce Adoption Tracker")
st.caption(
    "EIP-8250 adoption monitoring for the Glamsterdam upgrade. "
    "Pre-activation: simulator data. Post-activation: live mainnet via JSON-RPC."
)

# Sidebar controls
with st.sidebar:
    st.header("Data source")
    mode = st.radio("Mode", ["Simulator (pre-activation)", "Live (post-activation)"], index=0)
    if mode.startswith("Simulator"):
        seed = st.number_input("RNG seed", 0, 10_000_000, 42)
        num_senders = st.number_input("Number of senders", 100, 100_000, 5_000, step=500)
        num_blocks = st.number_input("Blocks to simulate", 10, 5_000, 500, step=50)
        start_block = st.number_input("Start block", 0, 10_000_000_000, 23_000_000)
    else:
        rpc_url = st.text_input("RPC URL", value=os.environ.get("RPC_URL", ""))
        start_block = st.number_input("Start block", 0, 10_000_000_000, 23_000_000)
        num_blocks = st.number_input("Blocks to fetch", 1, 1000, 100)
        st.info(
            "Live mode requires a Glamsterdam-aware execution node. Pre-activation, "
            "all transactions will appear as legacy (nonce_key=0)."
        )

    bucket_size = st.number_input("Block bucket size (for time-series)", 1, 1000, 50)
    run_button = st.button("Refresh data", type="primary")

# Data loading
if "txs" not in st.session_state or run_button:
    if mode.startswith("Simulator"):
        sim = KeyedNonceSimulator(num_senders=int(num_senders), rng_seed=int(seed))
        st.session_state["txs"] = list(sim.stream_blocks(int(start_block), int(num_blocks)))
    else:
        # Live mode requires async io within streamlit; stubbed for POC.
        # Production version: use asyncio.run with EthRpcClient.stream_transactions.
        st.warning(
            "Live mode integration is stubbed in this POC. The async RPC client "
            "in `src/rpc_client.py` is the production hook; wire it into the "
            "dashboard once a Glamsterdam testnet exposes the new fields."
        )
        st.session_state["txs"] = []

txs = st.session_state.get("txs", [])

if not txs:
    st.warning("No transactions loaded yet. Click 'Refresh data' to start.")
    st.stop()

# Headline metrics
overall = aggregate(txs)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total txs", f"{overall.total_txs:,}")
col2.metric("Adoption rate", f"{overall.adoption_rate * 100:.1f}%")
col3.metric("Senders using keyed", f"{overall.senders_using_keyed:,} / {overall.unique_senders:,}")
col4.metric("NONCE_MANAGER storage", _format_bytes(overall.nonce_manager_storage_bytes))

col5, col6, col7, col8 = st.columns(4)
col5.metric("Avg keys per keyed sender", f"{overall.avg_keys_per_keyed_sender:.2f}")
col6.metric("First-use allocations", f"{overall.first_use_count:,}")
col7.metric("Max seq observed", f"{overall.max_seq_observed:,}")
col8.metric("Key exhaustion headroom", f"{overall.key_exhaustion_headroom * 100:.4f}%")

# Time-series
st.subheader("Adoption over blocks")
series = bucket_by_block(txs, bucket_size=int(bucket_size))
df = pd.DataFrame([
    {
        "block_window_start": m.window_start_block,
        "adoption_rate": m.adoption_rate * 100,
        "sender_adoption_rate": m.sender_adoption_rate * 100,
        "first_use_count": m.first_use_count,
        "keyed_txs": m.keyed_txs,
        "legacy_txs": m.legacy_txs,
        "storage_bytes": m.nonce_manager_storage_bytes,
    }
    for m in series
])

if not df.empty:
    fig1 = px.line(
        df,
        x="block_window_start",
        y=["adoption_rate", "sender_adoption_rate"],
        labels={"value": "%", "block_window_start": "Block window start", "variable": "Metric"},
        title="Transaction-level vs sender-level adoption (%)",
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.bar(
        df,
        x="block_window_start",
        y=["keyed_txs", "legacy_txs"],
        title="Keyed vs legacy tx volume per window",
        labels={"value": "Transactions", "block_window_start": "Block window start", "variable": "Type"},
        barmode="stack",
    )
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.line(
        df,
        x="block_window_start",
        y="storage_bytes",
        title="Cumulative NONCE_MANAGER storage growth (bytes per window)",
        labels={"storage_bytes": "Bytes", "block_window_start": "Block window start"},
    )
    st.plotly_chart(fig3, use_container_width=True)

# Footer
st.caption(
    "Source: this dashboard reads the same internal model regardless of mode, "
    "so simulator-driven results structurally match what live mainnet data will "
    "produce once EIP-8250 activates at Glamsterdam fork. "
    "Spec: https://eips.ethereum.org/EIPS/eip-8250"
)
