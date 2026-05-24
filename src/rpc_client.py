"""Async JSON-RPC client for fetching Ethereum blocks.

Pre-Glamsterdam: this client can fetch current mainnet blocks via standard
`eth_getBlockByNumber`, but transactions will all have `nonce_key = 0` (legacy)
since EIP-8250 is not yet activated. The client is fully functional for
post-activation live mode.

Post-Glamsterdam activation: the Ethereum execution layer will expose the
keyed-nonce fields on each transaction. The exact JSON-RPC schema is still
being finalized in the EIP-8141 / EIP-8250 working group; this module
encapsulates that mapping so the rest of the codebase remains stable across
spec revisions.
"""
from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import aiohttp

from .data_models import KeyedNonceTransaction


class JsonRpcError(Exception):
    """JSON-RPC error response from upstream node."""


class EthRpcClient:
    """Minimal async JSON-RPC client for Ethereum execution layer.

    Use `from .rpc_client import EthRpcClient`. Provide RPC URL via constructor
    arg or `RPC_URL` env var.
    """

    def __init__(self, rpc_url: str | None = None, timeout_seconds: int = 30) -> None:
        self._url = rpc_url or os.environ.get("RPC_URL")
        if not self._url:
            raise ValueError(
                "RPC URL not configured; pass rpc_url=... or set RPC_URL env var"
            )
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None
        self._req_id = 0

    async def __aenter__(self) -> "EthRpcClient":
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _call(self, method: str, params: list) -> Any:
        if self._session is None:
            raise RuntimeError("Client not opened; use `async with EthRpcClient(...) as c:`")
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": self._req_id}
        async with self._session.post(self._url, data=json.dumps(payload),
                                       headers={"Content-Type": "application/json"}) as resp:
            resp.raise_for_status()
            body = await resp.json()
        if "error" in body:
            raise JsonRpcError(f"{method} -> {body['error']}")
        return body.get("result")

    async def get_block(self, block_number: int, full_txs: bool = True) -> dict:
        """Fetch a single block by number. Returns the raw block dict."""
        hex_num = hex(block_number)
        return await self._call("eth_getBlockByNumber", [hex_num, full_txs])

    async def stream_transactions(
        self,
        start_block: int,
        num_blocks: int,
    ) -> AsyncIterator[KeyedNonceTransaction]:
        """Stream transactions across a block range, mapping into our model.

        Pre-Glamsterdam: all txs map to `nonce_key=0`, `nonce_seq=tx.nonce`.
        Post-Glamsterdam: `nonceKey` and `nonceSeq` are read from the new
        transaction fields (final JSON-RPC schema TBD; mapping in
        `_map_tx_to_model` will update accordingly).
        """
        for offset in range(num_blocks):
            block = await self.get_block(start_block + offset, full_txs=True)
            if block is None:
                continue
            block_number = int(block["number"], 16)
            timestamp = int(block["timestamp"], 16)
            for tx in block.get("transactions", []):
                yield self._map_tx_to_model(tx, block_number, timestamp)

    @staticmethod
    def _map_tx_to_model(
        tx: dict, block_number: int, timestamp: int
    ) -> KeyedNonceTransaction:
        """Map a JSON-RPC transaction object into our internal model.

        Pre-activation: legacy nonce becomes `(nonce_key=0, nonce_seq=nonce)`.
        Post-activation: the execution-layer JSON-RPC will surface `nonceKey`
        and `nonceSeq` explicitly. The exact field names will be finalized
        during Glamsterdam scoping; update this mapper to match.
        """
        legacy_nonce = int(tx.get("nonce", "0x0"), 16) if isinstance(tx.get("nonce"), str) else int(tx.get("nonce", 0))
        # Forward-compatible: read new fields if present, fall back otherwise.
        nonce_key = int(tx.get("nonceKey", "0x0"), 16) if isinstance(tx.get("nonceKey"), str) else int(tx.get("nonceKey", 0))
        nonce_seq = (
            int(tx.get("nonceSeq", "0x0"), 16)
            if isinstance(tx.get("nonceSeq"), str)
            else int(tx.get("nonceSeq", legacy_nonce))
        )
        gas_used = int(tx.get("gas", "0x0"), 16) if isinstance(tx.get("gas"), str) else int(tx.get("gas", 0))
        is_first_use = bool(tx.get("isKeyedNonceFirstUse", False))

        return KeyedNonceTransaction(
            block_number=block_number,
            tx_hash=tx.get("hash", ""),
            sender=tx.get("from", "0x0"),
            nonce_key=nonce_key,
            nonce_seq=nonce_seq,
            gas_used=gas_used,
            is_first_use=is_first_use,
            timestamp=timestamp,
        )
