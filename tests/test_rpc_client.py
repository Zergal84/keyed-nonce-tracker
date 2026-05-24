"""Unit tests for the JSON-RPC client, using aioresponses to mock HTTP."""
from __future__ import annotations

import pytest
from aioresponses import aioresponses

from src.rpc_client import EthRpcClient, JsonRpcError

RPC_URL = "https://rpc.test.local"


def _block(number: int, timestamp: int, txs: list[dict]) -> dict:
    return {
        "number": hex(number),
        "timestamp": hex(timestamp),
        "transactions": txs,
    }


def _legacy_tx(tx_hash: str, sender: str, nonce: int, gas: int = 21000) -> dict:
    return {
        "hash": tx_hash,
        "from": sender,
        "nonce": hex(nonce),
        "gas": hex(gas),
    }


def _keyed_tx(
    tx_hash: str,
    sender: str,
    nonce_key: int,
    nonce_seq: int,
    gas: int = 50_000,
    first_use: bool = False,
) -> dict:
    return {
        "hash": tx_hash,
        "from": sender,
        "nonce": hex(nonce_seq),
        "nonceKey": hex(nonce_key),
        "nonceSeq": hex(nonce_seq),
        "gas": hex(gas),
        "isKeyedNonceFirstUse": first_use,
    }


def test_constructor_requires_url(monkeypatch):
    monkeypatch.delenv("RPC_URL", raising=False)
    with pytest.raises(ValueError, match="RPC URL not configured"):
        EthRpcClient()


def test_constructor_takes_env_var(monkeypatch):
    monkeypatch.setenv("RPC_URL", "https://env.example/")
    c = EthRpcClient()
    assert c._url == "https://env.example/"


def test_constructor_takes_explicit_arg():
    c = EthRpcClient(rpc_url="https://explicit.example/")
    assert c._url == "https://explicit.example/"


async def test_call_requires_open_session():
    c = EthRpcClient(rpc_url=RPC_URL)
    with pytest.raises(RuntimeError, match="Client not opened"):
        await c._call("eth_blockNumber", [])


async def test_get_block_legacy_only():
    block = _block(
        number=100,
        timestamp=1_700_000_000,
        txs=[_legacy_tx("0xaa", "0xSenderA", nonce=5)],
    )
    with aioresponses() as mocked:
        mocked.post(RPC_URL, payload={"jsonrpc": "2.0", "result": block, "id": 1})
        async with EthRpcClient(rpc_url=RPC_URL) as c:
            result = await c.get_block(100)
        assert result is not None
        assert result["number"] == "0x64"


async def test_stream_transactions_legacy():
    block = _block(
        number=100,
        timestamp=1_700_000_000,
        txs=[_legacy_tx("0xaa", "0xSenderA", nonce=5)],
    )
    with aioresponses() as mocked:
        mocked.post(RPC_URL, payload={"jsonrpc": "2.0", "result": block, "id": 1})
        async with EthRpcClient(rpc_url=RPC_URL) as c:
            txs = [tx async for tx in c.stream_transactions(start_block=100, num_blocks=1)]
        assert len(txs) == 1
        assert txs[0].is_legacy is True
        assert txs[0].nonce_key == 0
        assert txs[0].nonce_seq == 5
        assert txs[0].sender == "0xSenderA"
        assert txs[0].block_number == 100
        assert txs[0].timestamp == 1_700_000_000


async def test_stream_transactions_keyed():
    block = _block(
        number=200,
        timestamp=1_700_000_001,
        txs=[
            _keyed_tx("0xbb", "0xSenderB", nonce_key=7, nonce_seq=0, first_use=True),
            _keyed_tx("0xcc", "0xSenderB", nonce_key=7, nonce_seq=1),
        ],
    )
    with aioresponses() as mocked:
        mocked.post(RPC_URL, payload={"jsonrpc": "2.0", "result": block, "id": 1})
        async with EthRpcClient(rpc_url=RPC_URL) as c:
            txs = [tx async for tx in c.stream_transactions(start_block=200, num_blocks=1)]
        assert len(txs) == 2
        assert all(tx.is_keyed for tx in txs)
        assert txs[0].nonce_key == 7
        assert txs[0].is_first_use is True
        assert txs[1].is_first_use is False
        assert txs[1].nonce_seq == 1


async def test_stream_skips_missing_blocks():
    # Two requests: first returns None (block not yet mined), second returns a real block.
    blank = {"jsonrpc": "2.0", "result": None, "id": 1}
    block = _block(101, 1_700_000_002, [_legacy_tx("0xdd", "0xSenderC", nonce=0)])
    payload = {"jsonrpc": "2.0", "result": block, "id": 2}
    with aioresponses() as mocked:
        mocked.post(RPC_URL, payload=blank)
        mocked.post(RPC_URL, payload=payload)
        async with EthRpcClient(rpc_url=RPC_URL) as c:
            txs = [tx async for tx in c.stream_transactions(start_block=100, num_blocks=2)]
        # Block 100 was None, skipped. Block 101 has 1 tx.
        assert len(txs) == 1
        assert txs[0].block_number == 101


async def test_call_raises_on_rpc_error():
    with aioresponses() as mocked:
        mocked.post(RPC_URL, payload={"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1})
        async with EthRpcClient(rpc_url=RPC_URL) as c:
            with pytest.raises(JsonRpcError, match="Method not found"):
                await c.get_block(100)


def test_map_tx_handles_int_or_hex_nonce():
    # Robustness: some RPC implementations return ints not hex strings.
    tx_int = {"hash": "0x1", "from": "0xS", "nonce": 42, "gas": 21000}
    tx_hex = {"hash": "0x2", "from": "0xS", "nonce": "0x2a", "gas": "0x5208"}
    m_int = EthRpcClient._map_tx_to_model(tx_int, block_number=1, timestamp=1)
    m_hex = EthRpcClient._map_tx_to_model(tx_hex, block_number=1, timestamp=1)
    assert m_int.nonce_seq == m_hex.nonce_seq == 42
