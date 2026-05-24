# EIP dependency map

EIP-8250 does not stand alone. Several other EIPs in the Glamsterdam scope
extend or depend on the same frame-transaction substrate. This document
maps how they fit together, so a reader of this repo can see why the
internal model needs the fields it has.

## Direct dependency chain

```
EIP-8141 (Frame Transactions)
    ^
    | required by
    |
EIP-8250 (Keyed Nonces for Frame Transactions)
    ^
    | requires
    |
EIP-8266 (Expiring Nonces for Frame Transactions)
```

### EIP-8141: Frame Transactions

The base envelope. Defines a new transaction type whose payload carries
explicit nonce semantics that the keyed-nonce extensions then build on.
Without EIP-8141, EIP-8250 has nothing to attach a `(nonce_key, nonce_seq)`
pair to.

This project reads `nonceKey` and `nonceSeq` fields on the RPC transaction
object. Both originate in the EIP-8141 frame format. If EIP-8141 changes
the field names during scoping, the mapping in `src/rpc_client.py` is the
single point that needs updating.

### EIP-8250: Keyed Nonces for Frame Transactions

The headline EIP for this project. Replaces the linear nonce with a
`(nonce_key, nonce_seq)` pair where transactions on different non-zero keys
are replay-independent. Introduces the `NONCE_MANAGER` system contract and
the `KEYED_NONCE_FIRST_USE_GAS = 20000` surcharge that bounds new-slot
creation. The constants are mirrored in `src/data_models.py`.

### EIP-8266: Expiring Nonces for Frame Transactions

A second mode for EIP-8141 frame transactions: replay protection is bounded
by a deadline rather than the sender's account nonce. Slots in a sig-hash
ring buffer get freed when the deadline passes. This is orthogonal to
EIP-8250 but composes with it via the `expiry_verify` shared path. The
analyzer in this project does not track expiry mode in v0.1.0; that is a
candidate for a v0.2 extension after Glamsterdam ships.

## Related but separately scoped

### EIP-7928: Block Access Lists (BALs)

Glamsterdam adds block-level access lists. The simulator's per-sender
adoption profile already approximates what BAL data would look like at the
sender level. A future enhancement could cross-reference BAL data with
keyed-nonce activity to identify which contracts the keyed-nonce adopters
are actually calling.

### EIP-8268: Storage Roots in Block Access Lists

Extends EIP-7928 with per-account post-block storage trie roots. Useful for
partially stateful nodes; not directly relevant to the keyed-nonce
adoption question this project answers.

### EIP-7732: Enshrined Proposer-Builder Separation (ePBS)

The other consensus-layer headliner for Glamsterdam. Operationally
unrelated to EIP-8250 (consensus vs execution), but the two ship in the
same hard fork so adoption-tracking infrastructure for one upgrade should
ideally be reusable for both.

### EIP-7773: Glamsterdam hardfork meta

The umbrella spec that lists which EIPs are actually included. If EIP-8250
gets cut from Glamsterdam during scoping, this project's relevance shifts
to whatever follow-up fork includes it.

## Why this map matters

A common failure mode in single-EIP tooling is treating the EIP in
isolation, then breaking when an adjacent EIP changes a shared primitive.
By tracking the full frame-transaction dependency chain (EIP-8141 ->
EIP-8250 -> EIP-8266) in one document, the project stays oriented when
spec revisions land.

The mapping logic in `src/rpc_client.py` is deliberately conservative: it
reads forward-compatible field names if present, falls back to the legacy
linear nonce otherwise, and tolerates either int or hex-string encoding
since different RPC vendors disagree on which they emit.

## Sources

- EIP-8141: https://eips.ethereum.org/EIPS/eip-8141 (frame transactions)
- EIP-8250: https://eips.ethereum.org/EIPS/eip-8250 (keyed nonces)
- EIP-8266: https://eips.ethereum.org/EIPS/eip-8266 (expiring nonces)
- EIP-8268: https://eips.ethereum.org/EIPS/eip-8268 (storage roots in BALs)
- EIP-7928: https://eips.ethereum.org/EIPS/eip-7928 (block access lists)
- EIP-7732: https://eips.ethereum.org/EIPS/eip-7732 (ePBS)
- EIP-7773: https://eips.ethereum.org/EIPS/eip-7773 (Glamsterdam meta)
