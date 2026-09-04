# Submission field drafts

The exact strings to paste into the build page, versioned alongside the code
they describe. Counts held under the form limits (deletionImpact <= 600,
memoryWalkthrough <= 1200).

---

## deletionImpact  —  "What breaks when memory is deleted?"

Meritor prices uncollateralized credit between AI agents from a counterparty's
recalled history. Delete Sibyl Memory and every counterparty reverts to a
0-trust stranger: no SLA record, no repayment history, no disputes to score, so
the credit engine fails closed — every request drops to 150% collateral and
uncollateralized loans are denied. The PLATINUM agent that drew $50 at 0%
collateral one session ago is refused the identical request the next. Memory is
not a cache in front of the logic; it IS the creditworthiness.

---

## memoryWalkthrough  —  "judges score the 40% from this"

Persist: after every ACP job and Base settlement, Meritor writes a signed credit
event to Sibyl Memory — SLA outcome, repayment timing, dispute flags, Base tx
hash — as a journal entry plus a counterparty entity whose status mirrors its tier.

Recall (fresh session): a new process holds nothing in RAM. On a credit request
it reads the entity and replays the journal into an explainable 0-1000 score.
profile_as_of() rebuilds the score to any past instant, so a rejected agent is
shown the exact evidence held at decision time.

Changes the decision: the score sets a collateral tier that gates USDC on Base.
Session 1, 0xALPHA has no history → 150% collateral, denied. It works and repays
across sessions. A later fresh session recalls that record → PLATINUM, 0%
collateral, USDC released on Base. Wipe memory and the same agent, same request,
is denied again. Memory is the only variable.

Primitives: entities, events (journal), state (policy), FTS5 search, temporal
replay (score as-of a past instant), and reflection — a consolidation pass that
caps a deteriorating agent's tier in later sessions. The tier is then published
to Base as a portable EAS attestation.


---

## memoryPrimitives checkboxes — tick these 6 of 7 (all genuinely exercised)

- [x] **recall** — every credit decision recalls the counterparty profile
- [x] **entities** — counterparty profiles, tier mirrored into entity status
- [x] **semantic search** — FTS5 search across profiles ("who has a dispute")
- [x] **temporal / time-travel** — `profile_as_of()` replays the score to a past instant
- [x] **reflection** — the consolidation pass derives trend/volatility into a memo
- [x] **consolidation** — the memo is a durable, compacted read persisted to reference storage
- [ ] summarization — not used (no LLM summarizer in the credit path)

---

## postUrls — the two build-in-public posts

Tag **@sibylcap** (required) and each claimed partner: **@base** (or
@buildonbase) and **@virtuals_io**. Platform: X or Farcaster. Post the build-log
now and the demo video when recorded; paste both URLs, one per line.
