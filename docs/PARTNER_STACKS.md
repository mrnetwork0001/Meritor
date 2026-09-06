# Partner stacks - how each one does real work in Meritor

The hackathon multiplier is earned only when a judge can see a stack *doing real
work in the demo, serving the product's actual function*. This document maps each
claimed stack to the exact moment it runs and the command that runs it.

## Sibyl Memory (mandatory, load-bearing - not a multiplier)

The credit engine has no state of its own. Every score is recalled from Sibyl
Memory, and `meritor wipe` collapses the whole system to 0-trust. See the README.

## Base - a recalled tier releases USDC onchain

**What a judge sees:** a PLATINUM counterparty, recalled from memory in a fresh
session, is approved at 0% collateral, and Meritor releases the principal on Base.
The confirmed transaction hash is written back to memory as a `LOAN_DISBURSED`
event and resolves on Basescan on screen.

**Qualifying action:** an executed onchain USDC transfer (a contract interaction
plus a wallet operation - two of the four actions the rules name).

```bash
# one-time: fund the settlement wallet on Base Sepolia
#   ETH for gas + USDC to disburse, at https://faucet.circle.com
#   address is printed by:  grep BASE_PRIVATE_KEY .env  then derive, or:
python -c "from eth_account import Account; import os,dotenv; dotenv.load_dotenv(); \
print(Account.from_key(os.environ['BASE_PRIVATE_KEY']).address)"

# release the approved principal to a counterparty, live on Base Sepolia
python -m meritor.cli request 0xALPHA 50 --settle 0x<counterparty-address>
```

The settler refuses to broadcast on the wrong chain and never fabricates a hash:
with no key, no funds, or an unreachable RPC it returns `DRY_RUN` with the reason.

**Networks (verified live):** Base Sepolia `84532` (`https://sepolia.base.org`),
Base mainnet `8453` (`https://mainnet.base.org`). USDC has 6 decimals on both;
Circle's canonical addresses are built in.

**Optional premium path (x402):** the `x402` v2 Python SDK (`pip install
"x402[httpx]"`) settles on the public Base Sepolia facilitator. Meritor's product
framing - agents paying to pull a counterparty's premium credit report - is a
natural x402 use, but a plain settlement already qualifies, so x402 is an
enhancement, not the qualifying action.

## Virtuals ACP - job outcomes feed the credit history

**What a judge sees:** Meritor dispatches a job on the Agent Commerce Protocol;
when it completes, that outcome is written to memory as an SLA credit event -
which is where the recalled reliability score comes from in the first place.

**Qualifying action:** a transacting ACP agent (a created + funded job), or at
minimum a registered agent Meritor genuinely dispatches to.

```bash
# one-time auth (opens app.virtuals.io; free)
npx acp configure
npx acp agent create        # provisions the agent's onchain wallet  (first cost gate)
npx acp agent add-signer    # P256 signer, browser-approved

# dispatch a real job; its completion becomes a credit event
python -m meritor.cli acp-job 0xALPHA --offering risk-audit --budget 10
```

**Toolchain reality:**
- The Python ACP SDK (`virtuals-acp`) is abandoned - pinned below Python 3.13 and
  built on a primitive ACP v2 removed. The maintained path is
  `@virtuals-protocol/acp-cli` (Node ≥ 20.19), wrapped as a subprocess.
- `IS_TESTNET=true` exposes Base Sepolia (`84532`) in `acp chain list`, but its
  auth frontend (`app-dev.virtuals.io`) is behind HTTP Basic Auth not issued to
  participants. Mainnet auth (`app.virtuals.io`) is open. Ask in Discord whether
  teams get testnet dev credentials; otherwise the ACP job runs on mainnet.
- `--mock` runs the full job lifecycle offline for testing and for a demo take
  that does not depend on a funded ACP wallet. A mock run is clearly labelled as
  such and must not be presented as a live settlement.

## Multiplier arithmetic (from the rules, verbatim)

> "+15% for the first, +10% for the second, capped at x1.25."

Ordinal, not per-partner: whichever stack a judge verifies *first* is the +15%.
Additive on the published table (`1 → x1.15`, `2 → x1.25`), confirmed by the
site's own worked example (`82 × 1.25 = 102.5`). Sibyl is mandatory and is never
a multiplier.
