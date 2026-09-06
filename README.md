# 🛡️ Meritor

**A load-bearing credit memory for AI agents that lend to each other.**

Meritor turns [Sibyl Memory](https://sibyllabs.org) into a dynamic credit engine
for onchain agent fleets. Agents that can remember a counterparty's track record
across sessions can extend *uncollateralized* credit; agents that forget must
demand 150%+ collateral from everyone, every time. Meritor is that memory.

> Built for the Sibyl Labs Hackathon (Sep 2026). Apache-2.0.

---

## The one-sentence version

Recall a counterparty's repayment history → change its collateral tier → change
a real USDC disbursement on Base. Delete the memory and the exact same agent,
making the exact same request, is refused.

## Why this is load-bearing, not decorative

The credit score is a **pure function of recalled memory**. There is no cache in
front of the logic that memory merely accelerates - the memory *is* the input.
Concretely:

- **Fail-closed by construction.** The `MemoryBackend` contract has no graceful
  degradation path. An unreachable substrate raises `MemoryUnavailable`, which
  propagates to the decision boundary and becomes an explicit 0-trust rejection.
  It is never caught-and-defaulted to an empty profile, because an empty profile
  reads as "new counterparty, clean record" - which would let an outage silently
  approve credit. See [`meritor/memory/base.py`](meritor/memory/base.py).
- **The deletion test.** `meritor wipe --yes` erases the Sibyl Memory namespace.
  After it, every credit decision collapses to `UNKNOWN` / 150% / denied. Nothing
  else in the system changes.

## The fresh-session beat

Every step below is a **separate process**. Nothing survives in RAM between them.
`MERITOR_SESSION_ID` marks the logical session boundary.

| Step | Process | Result |
|---|---|---|
| Seed 0xALPHA's prior history | - | 3 sessions of clean settlement, backdated |
| 0xBETA (never seen) requests $50 | session A | **DENIED**, 150% collateral, `memory-backed: False` |
| 0xALPHA requests the same $50 | session A | **APPROVED**, **0% collateral**, PLATINUM |
| 0xBETA works + repays | session A | one clean event written |
| 0xBETA returns | **session B, fresh process** | **APPROVED**, 120% - the record changed the decision |
| Time-travel 0xALPHA | session B | GOLD as of 10 days ago, PLATINUM today |
| `wipe --yes` | - | Sibyl Memory erased |
| 0xALPHA repeats the request | **session C, fresh process** | **DENIED** - memory was the only variable |

Run it:

```bash
./demo/fresh_session_demo.sh
```

## The four memory primitives (and two more on Pro)

Meritor uses Sibyl Memory as more than a key-value store, because the 40%
criterion rewards coordination and dynamic-storage patterns over plain recall.

| Primitive | Sibyl surface | What it carries |
|---|---|---|
| **entities** | `set_entity` / `get_entity` | the counterparty profile; tier mirrored into `status` for portfolio sweeps by risk band |
| **events** | `write_event` / `read_events` | the append-only credit journal - what makes the score reconstructible, not just current |
| **state** | `set_state` / `get_state` | the collateral policy in force, and live exposure |
| **search** | `search_entities` (FTS5) | "which counterparties have a dispute on record" without a table scan |
| **temporal** | journal replay | `profile_as_of(agent, instant)` rebuilds the score at any past moment |
| **reflection** | journal → `set_reference` | a consolidation pass over the journal that caps a deteriorating agent's tier in future sessions (hand-rolled; free-tier) |

> Reflection is hand-rolled rather than using Sibyl's native `learn()` on
> purpose: `learn()` is gated to paid tier strings the hackathon Pro grant does
> not set (`_PAID_ONLY_TIERS` in the SDK has no `"pro"`), so it would raise for
> us and for a judge re-running the demo. Our pass uses only journal reads and
> reference writes, which every tier has.

## Architecture

```
        Sibyl Memory  (local SQLite substrate - no API key, no network)
              │  recall / journal-replay              ▲  write-back
              ▼                                       │
        Credit engine  ──►  tier  ──┬──►  Base Settler ──►  USDC on Base
      (pure, explainable)            ├──►  EAS Attester ──►  portable onchain tier (Base)
                                     └──►  Virtuals ACP  ──►  job dispatch → credit events
```

- **Sibyl Memory** - mandatory, load-bearing. A local SQLite file the agent owns;
  deleting it is a real experiment, not a mocked failure.
- **Base** - a recalled tier is published to Base as a portable **EAS
  attestation** (the private reasoning stays in memory; the result becomes a
  verifiable onchain claim other agents consume), and can release USDC; the
  attestation UID / tx hash is written back to memory as provenance.
- **Virtuals ACP** - job dispatch/settlement on the Agent Commerce Protocol; each
  completed job becomes a credit event.

## Setup

```bash
git clone https://github.com/mrnetwork0001/Meritor.git && cd Meritor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # installs sibyl-memory-client==0.8.0
export MEMORY_DRIVER=sibyl
export SIBYL_MEMORY_DB=.meritor/meritor.db
python -m meritor.cli status
```

`sibyl-memory-client` is pinned to `0.8.0` deliberately: it shipped one day
before the build window with commits still landing, and an unpinned upgrade
mid-window could invalidate a recorded demo.

For the partner stacks, copy `.env.example` to `.env` and fill in a Base Sepolia
key (see [`docs/PARTNER_STACKS.md`](docs/PARTNER_STACKS.md)).

## Web frontend

A landing page and an interactive **credit desk**, served locally and backed by
the *real* engine - not a mockup. The desk's deletion-test switch actually
erases a live Sibyl Memory database, so recall genuinely collapses to 0-trust.

```bash
pip install -r requirements.txt          # includes fastapi + uvicorn
python -m uvicorn web.server:app --port 8848
open http://127.0.0.1:8848               # landing page; the desk is at /desk
```

The API is live against the engine: `GET /api/agents`, `POST /api/decision`,
and `POST /api/memory/wipe` | `/restore` (the deletion test over HTTP).

## Tests

```bash
pip install pytest && python -m pytest -q
```

The suite locks the invariants that make memory load-bearing: no uncollateralized
credit without recalled memory, a memory outage is never mistaken for a clean
slate, and a single good session cannot reach the 0-collateral tier.

## Prior Work declaration

This repository was built for the Sibyl Labs Hackathon during the Sep 1–10 build
window. Pre-existing material carried in from before the window:

- The project concept and specification documents (`MERITOR_PROJECT_SPEC.md`,
  `ANTIGRAVITY_MERITOR.md`, `.agents/skills/meritor-sibyl/SKILL.md`), authored
  Aug 20, 2026. These were planning artifacts; note that several of their
  technical assumptions (a hosted Sibyl "API" with a key) proved wrong on
  contact with the real SDK and were corrected in code.
- All integration code - the credit engine, the Sibyl/Base/Virtuals drivers, the
  CLI, the demo harness, and the tests - was written during the build window and
  is visible in this repository's commit history.
- Dependencies are third-party libraries under their own licenses:
  `sibyl-memory-client` (MIT), `x402` (Apache-2.0), `web3.py`, `pydantic`,
  and the `@virtuals-protocol/acp-cli` toolchain.

## License

[Apache-2.0](LICENSE).
