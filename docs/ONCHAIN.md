# Live onchain evidence (Base mainnet)

Meritor's Base partner-stack integration, executed live on **Base mainnet
(chain 8453)**. Every artifact below is independently verifiable — the
attestation is not a claim in a slide, it is a row in EAS on Base.

## EAS credit-tier attestation

Meritor recalled 0xALPHA's credit history from Sibyl Memory, scored it to
PLATINUM, and published that tier to Base as an EAS attestation. Reading the
attestation back from the EAS contract decodes to exactly the recalled state.

| Field | Value |
|---|---|
| Network | Base mainnet (8453) |
| Attester | `0x9A509d5343654A0f7924Dd1Bc2aA500a2fB009e3` |
| Schema UID | `0xe90e689cd532b7777b444b3522a9c0a3bbdc04e230982548b4884bd4e5f6697c` |
| Schema | `string agentId,uint16 score,string tier,uint32 evidenceCount,uint16 sessions,uint64 assessedAt` |
| Attestation UID | `0x66c791a420a61bcd3d33bf6c8ba8c6fe54b8dcdfe13852c8da7077bfdd9a0e2a` |
| Tx hash | `0xfcb465afde7eecb91727fec2c5315560ab374f9fad3ae8873db4ce5b13110f61` |
| Block | 50862970 |
| Decoded payload | `agentId=0xALPHA, score=856, tier=PLATINUM, evidenceCount=25, sessions=4` |

**View:**
- Attestation → https://base.easscan.org/attestation/view/0x66c791a420a61bcd3d33bf6c8ba8c6fe54b8dcdfe13852c8da7077bfdd9a0e2a
- Transaction → https://basescan.org/tx/0xfcb465afde7eecb91727fec2c5315560ab374f9fad3ae8873db4ce5b13110f61
- Schema → https://base.easscan.org/schema/view/0xe90e689cd532b7777b444b3522a9c0a3bbdc04e230982548b4884bd4e5f6697c

The attestation UID is written back to Sibyl Memory as a `LOAN_DISBURSED`
provenance event, closing the loop: memory → tier → onchain → memory.

## Why this is the load-bearing part, not decoration

The attested payload — `score=856, tier=PLATINUM` — is a *function of recalled
memory*. Wipe Sibyl Memory and Meritor has no basis to attest anything but
UNKNOWN. The onchain record is downstream of the memory, never a substitute for
it. Reproduce with:

```bash
python -m meritor.cli seed 0xALPHA --sessions 3 --per-session 4
python -m meritor.cli attest 0xALPHA        # broadcasts on the configured chain
```

Gas: the full register-schema + attest cost ~0.0000034 ETH on Base mainnet.

## Virtuals ACP — a registered on-chain agent

Meritor is registered on the Agent Commerce Protocol as a live, discoverable
agent, with an on-chain ERC-8004 identity on Base mainnet.

| Field | Value |
|---|---|
| Agent | `Meritor` (role HYBRID) |
| ACP agent id | `01a075bc-bf93-73e3-a1bd-cc0904791ab3` |
| Agent wallet | `0xcd1e56694767cb4ab26ca87abcce5e964c41a196` |
| **ERC-8004 identity (Base 8453)** | **agent #84921**, active |
| Offering | `meritor_credit_report` — memory-backed credit underwriting, 0.05 USDC, SLA 60m |

The offering is Meritor's own product exposed to the agent economy: give it a
counterparty and a requested line, it recalls the history and returns a tier,
score, and collateral ratio — and fails closed to 0-trust if memory is gone.

Reproduce (needs `npx acp configure` + a signer):
```bash
npx acp agent whoami --json          # shows the ERC-8004 id and the offering
```

> Note: a full escrow *job* (create-job → fund → complete) additionally depends
> on Virtuals' event-stream endpoint, which was intermittently unreachable
> (`fetch failed`) from the build network. The registration and offering above
> are stream-independent and confirmed on-chain.
