"""Base settlement — where a recalled credit tier becomes money moving.

This is the agent that closes the loop. The credit engine turns memory into a
tier; the settler turns a tier into a USDC disbursement on Base. Without the
memory layer there is no tier, so there is nothing here to authorize.

One rule, absolutely: this module never invents a transaction hash. If there is
no key, no funding, or no RPC, it says so and returns a DRY_RUN result. A demo
that shows a fabricated hash is worse than a demo that shows none.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

# Circle's canonical USDC deployments. 6 decimals on both networks.
USDC_ADDRESSES: dict[int, str] = {
    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",   # Base mainnet
    84532: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # Base Sepolia
}
USDC_DECIMALS = 6

DEFAULT_RPC: dict[int, str] = {
    8453: "https://mainnet.base.org",
    84532: "https://sepolia.base.org",
}

EXPLORER: dict[int, str] = {
    8453: "https://basescan.org/tx/",
    84532: "https://sepolia.basescan.org/tx/",
}

# Minimal ERC-20 surface. Enough to transfer and to read balances for the demo.
ERC20_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "decimals",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
    },
]


class SettlementStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    DRY_RUN = "DRY_RUN"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


@dataclass
class Settlement:
    status: SettlementStatus
    amount_usdc: float
    to_address: str | None = None
    tx_hash: str | None = None
    explorer_url: str | None = None
    chain_id: int | None = None
    detail: str = ""

    @property
    def is_onchain(self) -> bool:
        """True only when a real transaction was broadcast and confirmed."""
        return self.status is SettlementStatus.CONFIRMED and bool(self.tx_hash)

    def render(self) -> str:
        lines = [f" settlement       : {self.status.value}"]
        if self.to_address:
            lines.append(f" beneficiary      : {self.to_address}")
        lines.append(f" amount           : ${self.amount_usdc:,.2f} USDC")
        if self.tx_hash:
            lines.append(f" tx hash          : {self.tx_hash}")
        if self.explorer_url:
            lines.append(f" explorer         : {self.explorer_url}")
        if self.detail:
            lines.append(f"\n {self.detail}")
        return "\n".join(lines)


class BaseSettler:
    """Releases USDC on Base once the credit engine has authorized it."""

    def __init__(
        self,
        rpc_url: str | None = None,
        chain_id: int = 84532,
        private_key: str | None = None,
        usdc_address: str | None = None,
    ) -> None:
        self.chain_id = chain_id
        self.rpc_url = rpc_url or DEFAULT_RPC.get(chain_id)
        self.private_key = private_key
        self.usdc_address = usdc_address or USDC_ADDRESSES.get(chain_id)
        self._w3: Any = None
        self._account: Any = None

    # --- connection -------------------------------------------------------

    @property
    def configured(self) -> bool:
        return bool(self.rpc_url and self.private_key and self.usdc_address)

    def connect(self) -> tuple[bool, str]:
        """Best-effort connect. Returns (ok, detail) rather than raising."""
        if not self.private_key:
            return False, "BASE_PRIVATE_KEY is not set — no wallet to settle from."
        if not self.rpc_url:
            return False, f"no RPC URL for chain {self.chain_id}."
        if not self.usdc_address:
            return False, f"no USDC address known for chain {self.chain_id}."
        try:
            from eth_account import Account
            from web3 import Web3

            w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if not w3.is_connected():
                return False, f"could not reach {self.rpc_url}."
            actual = w3.eth.chain_id
            if actual != self.chain_id:
                return False, (
                    f"RPC at {self.rpc_url} reports chain {actual}, expected "
                    f"{self.chain_id}. Refusing to settle on the wrong network."
                )
            self._w3 = w3
            self._account = Account.from_key(self.private_key)
            return True, f"connected to chain {actual} as {self._account.address}"
        except Exception as exc:
            return False, f"connection failed: {exc}"

    def address(self) -> str | None:
        return self._account.address if self._account else None

    def usdc_balance(self) -> Decimal | None:
        if self._w3 is None or self._account is None:
            return None
        try:
            token = self._w3.eth.contract(
                address=self._w3.to_checksum_address(self.usdc_address), abi=ERC20_ABI
            )
            raw = token.functions.balanceOf(self._account.address).call()
            return Decimal(raw) / Decimal(10**USDC_DECIMALS)
        except Exception:
            return None

    # --- settlement -------------------------------------------------------

    def disburse(
        self, to_address: str, amount_usdc: float, *, dry_run: bool = False
    ) -> Settlement:
        """Transfer USDC on Base to an approved counterparty."""
        if amount_usdc <= 0:
            return Settlement(
                status=SettlementStatus.NOT_AUTHORIZED,
                amount_usdc=amount_usdc,
                to_address=to_address,
                detail="Credit engine authorized nothing to disburse.",
            )

        ok, detail = self.connect()
        if not ok or dry_run:
            return Settlement(
                status=SettlementStatus.DRY_RUN,
                amount_usdc=amount_usdc,
                to_address=to_address,
                chain_id=self.chain_id,
                detail=(
                    f"DRY RUN — no transaction was broadcast. {detail}"
                    if not ok
                    else "DRY RUN requested — no transaction was broadcast."
                ),
            )

        try:
            w3 = self._w3
            token = w3.eth.contract(
                address=w3.to_checksum_address(self.usdc_address), abi=ERC20_ABI
            )
            raw_amount = int(Decimal(str(amount_usdc)) * Decimal(10**USDC_DECIMALS))
            to = w3.to_checksum_address(to_address)

            tx = token.functions.transfer(to, raw_amount).build_transaction(
                {
                    "from": self._account.address,
                    "nonce": w3.eth.get_transaction_count(self._account.address),
                    "chainId": self.chain_id,
                }
            )
            signed = self._account.sign_transaction(tx)
            raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
            tx_hash = w3.eth.send_raw_transaction(raw)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            h = tx_hash.hex()
            if not h.startswith("0x"):
                h = "0x" + h
            url = EXPLORER.get(self.chain_id, "") + h
            confirmed = receipt.get("status") == 1
            return Settlement(
                status=SettlementStatus.CONFIRMED if confirmed else SettlementStatus.FAILED,
                amount_usdc=amount_usdc,
                to_address=to,
                tx_hash=h,
                explorer_url=url,
                chain_id=self.chain_id,
                detail=(
                    "USDC released on Base against a memory-derived credit tier."
                    if confirmed
                    else "Transaction reverted onchain."
                ),
            )
        except Exception as exc:
            return Settlement(
                status=SettlementStatus.FAILED,
                amount_usdc=amount_usdc,
                to_address=to_address,
                chain_id=self.chain_id,
                detail=f"settlement error: {exc}",
            )
