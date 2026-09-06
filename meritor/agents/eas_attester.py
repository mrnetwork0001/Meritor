"""EAS attestations on Base - publishing a recalled credit tier onchain.

The division of labour is the whole idea. Meritor's *reasoning* - the full
journal, the decayed score, the evidence behind a tier - is load-bearing and
private, and it lives in Sibyl Memory. The *result* - "this agent is PLATINUM as
of now, on this evidence" - is a portable, verifiable claim other agents in the
economy can consume without Meritor's memory or trust. EAS is how that result
leaves the machine: an onchain attestation on Base, anchored to the memory that
produced it.

This satisfies the Base partner stack by interacting with EAS's already-deployed
contract (the Sibyl team confirmed that interacting with a deployed contract
meets the deployment floor - no need to deploy our own). EAS is an OP-Stack
predeploy, so the same addresses serve Base mainnet and Base Sepolia.

Like the settler, this never fabricates an attestation UID. No key, no funding,
or an unreachable RPC returns a DRY_RUN carrying the exact payload that WOULD
have been attested, so the demo is honest either way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# EAS OP-Stack predeploys - identical on Base mainnet (8453) and Base Sepolia
# (84532). Verified live (code present) and against the official EAS registry.
EAS_ADDRESS = "0x4200000000000000000000000000000000000021"
SCHEMA_REGISTRY_ADDRESS = "0x4200000000000000000000000000000000000020"

EAS_EXPLORER: dict[int, str] = {
    8453: "https://base.easscan.org/attestation/view/",
    84532: "https://base-sepolia.easscan.org/attestation/view/",
}
TX_EXPLORER: dict[int, str] = {
    8453: "https://basescan.org/tx/",
    84532: "https://sepolia.basescan.org/tx/",
}

# The Meritor credit schema. Field order defines the ABI encoding.
SCHEMA_STRING = (
    "string agentId,uint16 score,string tier,"
    "uint32 evidenceCount,uint16 sessions,uint64 assessedAt"
)
SCHEMA_TYPES = ["string", "uint16", "string", "uint32", "uint16", "uint64"]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Minimal EAS surface: attest() and SchemaRegistry.register() / getSchema().
EAS_ABI = [
    {
        "name": "attest",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {
                "name": "request",
                "type": "tuple",
                "components": [
                    {"name": "schema", "type": "bytes32"},
                    {
                        "name": "data",
                        "type": "tuple",
                        "components": [
                            {"name": "recipient", "type": "address"},
                            {"name": "expirationTime", "type": "uint64"},
                            {"name": "revocable", "type": "bool"},
                            {"name": "refUID", "type": "bytes32"},
                            {"name": "data", "type": "bytes"},
                            {"name": "value", "type": "uint256"},
                        ],
                    },
                ],
            }
        ],
        "outputs": [{"name": "", "type": "bytes32"}],
    },
    {
        "name": "Attested",
        "type": "event",
        "anonymous": False,
        "inputs": [
            {"name": "recipient", "type": "address", "indexed": True},
            {"name": "attester", "type": "address", "indexed": True},
            {"name": "uid", "type": "bytes32", "indexed": False},
            {"name": "schemaUID", "type": "bytes32", "indexed": True},
        ],
    },
]

SCHEMA_REGISTRY_ABI = [
    {
        "name": "register",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "schema", "type": "string"},
            {"name": "resolver", "type": "address"},
            {"name": "revocable", "type": "bool"},
        ],
        "outputs": [{"name": "", "type": "bytes32"}],
    },
    {
        "name": "getSchema",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "uid", "type": "bytes32"}],
        "outputs": [
            {
                "name": "",
                "type": "tuple",
                "components": [
                    {"name": "uid", "type": "bytes32"},
                    {"name": "resolver", "type": "address"},
                    {"name": "revocable", "type": "bool"},
                    {"name": "schema", "type": "string"},
                ],
            }
        ],
    },
]


def compute_schema_uid(
    schema: str = SCHEMA_STRING, resolver: str = ZERO_ADDRESS, revocable: bool = True
) -> str:
    """EAS derives a schema UID deterministically; no registry read needed."""
    from eth_abi.packed import encode_packed
    from eth_utils import keccak

    return "0x" + keccak(
        encode_packed(["string", "address", "bool"], [schema, resolver, revocable])
    ).hex()


class AttestStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    DRY_RUN = "DRY_RUN"


@dataclass
class Attestation:
    status: AttestStatus
    agent_id: str
    score: int
    tier: str
    schema_uid: str
    uid: str | None = None
    tx_hash: str | None = None
    attestation_url: str | None = None
    tx_url: str | None = None
    chain_id: int | None = None
    detail: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def is_onchain(self) -> bool:
        return self.status is AttestStatus.CONFIRMED and bool(self.uid)

    def render(self) -> str:
        lines = [
            f" attestation      : {self.status.value}",
            f" subject          : {self.agent_id}",
            f" claim            : {self.tier} ({self.score}/1000)",
            f" schema           : {self.schema_uid}",
        ]
        if self.uid:
            lines.append(f" attestation UID  : {self.uid}")
        if self.tx_hash:
            lines.append(f" tx hash          : {self.tx_hash}")
        if self.attestation_url:
            lines.append(f" view on EAS      : {self.attestation_url}")
        if self.detail:
            lines.append(f"\n {self.detail}")
        return "\n".join(lines)


class EASAttester:
    """Publishes Meritor credit tiers as EAS attestations on Base."""

    def __init__(
        self,
        rpc_url: str | None = None,
        chain_id: int = 84532,
        private_key: str | None = None,
        schema_uid: str | None = None,
    ) -> None:
        self.chain_id = chain_id
        self.rpc_url = rpc_url or {
            8453: "https://mainnet.base.org",
            84532: "https://sepolia.base.org",
        }.get(chain_id)
        self.private_key = private_key
        self.schema_uid = schema_uid or compute_schema_uid()
        self._w3: Any = None
        self._account: Any = None

    def connect(self) -> tuple[bool, str]:
        if not self.private_key:
            return False, "BASE_PRIVATE_KEY is not set - no wallet to attest from."
        if not self.rpc_url:
            return False, f"no RPC URL for chain {self.chain_id}."
        try:
            from eth_account import Account
            from web3 import Web3

            w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if not w3.is_connected():
                return False, f"could not reach {self.rpc_url}."
            actual = w3.eth.chain_id
            if actual != self.chain_id:
                return False, f"RPC reports chain {actual}, expected {self.chain_id}."
            self._w3 = w3
            self._account = Account.from_key(self.private_key)
            return True, f"connected to chain {actual} as {self._account.address}"
        except Exception as exc:
            return False, f"connection failed: {exc}"

    def address(self) -> str | None:
        return self._account.address if self._account else None

    def schema_registered(self) -> bool:
        """True if our schema UID resolves onchain (idempotent registration)."""
        if self._w3 is None:
            return False
        try:
            reg = self._w3.eth.contract(
                address=self._w3.to_checksum_address(SCHEMA_REGISTRY_ADDRESS),
                abi=SCHEMA_REGISTRY_ABI,
            )
            got = reg.functions.getSchema(bytes.fromhex(self.schema_uid[2:])).call()
            return bool(got[3])  # non-empty schema string
        except Exception:
            return False

    def register_schema(self) -> str | None:
        """Register the Meritor schema if absent. Returns a tx hash or None."""
        ok, _ = self.connect() if self._w3 is None else (True, "")
        if not ok or self._w3 is None:
            return None
        if self.schema_registered():
            return None
        reg = self._w3.eth.contract(
            address=self._w3.to_checksum_address(SCHEMA_REGISTRY_ADDRESS),
            abi=SCHEMA_REGISTRY_ABI,
        )
        tx = reg.functions.register(SCHEMA_STRING, ZERO_ADDRESS, True).build_transaction(
            {
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "chainId": self.chain_id,
            }
        )
        signed = self._account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        h = self._w3.eth.send_raw_transaction(raw)
        self._w3.eth.wait_for_transaction_receipt(h, timeout=120)
        return h.hex()

    def _encode(self, agent_id: str, score: int, tier: str, evidence: int,
                sessions: int, assessed_at: int) -> bytes:
        from eth_abi import encode

        return encode(SCHEMA_TYPES, [agent_id, score, tier, evidence, sessions, assessed_at])

    def attest_credit(
        self,
        agent_id: str,
        score: int,
        tier: str,
        evidence: int,
        sessions: int,
        assessed_at: int,
        *,
        recipient: str | None = None,
        dry_run: bool = False,
    ) -> Attestation:
        """Publish one credit-tier attestation to Base via EAS."""
        payload = {
            "agentId": agent_id, "score": score, "tier": tier,
            "evidenceCount": evidence, "sessions": sessions, "assessedAt": assessed_at,
        }

        ok, detail = self.connect()
        if not ok or dry_run:
            return Attestation(
                status=AttestStatus.DRY_RUN, agent_id=agent_id, score=score, tier=tier,
                schema_uid=self.schema_uid, chain_id=self.chain_id, payload=payload,
                detail=(f"DRY RUN - nothing attested onchain. {detail}" if not ok
                        else "DRY RUN requested - nothing attested onchain."),
            )

        try:
            # A recipient that is a real address anchors the attestation to that
            # agent's wallet; our demo ids are not addresses, so default to zero.
            rcpt = recipient if (recipient and recipient.startswith("0x") and len(recipient) == 42) else ZERO_ADDRESS

            reg_tx = self.register_schema()  # idempotent: no-op if already onchain
            if reg_tx is not None:
                # Public RPCs are load-balanced, so a just-mined registration can
                # be invisible to the node that serves the next gas estimate
                # (read-after-write lag). Poll until the schema is visible before
                # attesting, so the first run is as reliable as later ones.
                for _ in range(20):
                    if self.schema_registered():
                        break

            eas = self._w3.eth.contract(
                address=self._w3.to_checksum_address(EAS_ADDRESS), abi=EAS_ABI
            )
            data = self._encode(agent_id, score, tier, evidence, sessions, assessed_at)
            request = (
                bytes.fromhex(self.schema_uid[2:]),
                (
                    self._w3.to_checksum_address(rcpt),
                    0,                       # expirationTime: no expiry
                    True,                    # revocable
                    b"\x00" * 32,            # refUID: none
                    data,
                    0,                       # value
                ),
            )
            tx = eas.functions.attest(request).build_transaction(
                {
                    "from": self._account.address,
                    "nonce": self._w3.eth.get_transaction_count(self._account.address),
                    "chainId": self.chain_id,
                    "value": 0,
                }
            )
            signed = self._account.sign_transaction(tx)
            raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
            tx_hash = self._w3.eth.send_raw_transaction(raw)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            confirmed = receipt.get("status") == 1

            # The real UID is emitted in the Attested event, not recoverable by a
            # second simulated call (which would compute a *different* UID). Parse
            # it out of this transaction's own receipt.
            uid = None
            if confirmed:
                events = eas.events.Attested().process_receipt(receipt)
                if events:
                    raw_uid = events[0]["args"]["uid"]
                    uid = "0x" + (raw_uid.hex() if isinstance(raw_uid, (bytes, bytearray)) else str(raw_uid))
            h = tx_hash.hex()
            if not h.startswith("0x"):
                h = "0x" + h
            ok_uid = confirmed and uid is not None
            return Attestation(
                status=AttestStatus.CONFIRMED if ok_uid else AttestStatus.FAILED,
                agent_id=agent_id, score=score, tier=tier, schema_uid=self.schema_uid,
                uid=uid,
                tx_hash=h,
                attestation_url=(EAS_EXPLORER.get(self.chain_id, "") + uid) if ok_uid else None,
                tx_url=TX_EXPLORER.get(self.chain_id, "") + h,
                chain_id=self.chain_id, payload=payload,
                detail=("Credit tier published to Base as a portable EAS attestation."
                        if ok_uid else
                        ("Transaction reverted." if not confirmed
                         else "Confirmed but no Attested event found in receipt.")),
            )
        except Exception as exc:
            return Attestation(
                status=AttestStatus.FAILED, agent_id=agent_id, score=score, tier=tier,
                schema_uid=self.schema_uid, chain_id=self.chain_id, payload=payload,
                detail=f"attestation error: {exc}",
            )
