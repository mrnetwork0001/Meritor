"""Reflection - consolidating the journal into durable underwriting policy.

The point-in-time score answers "how creditworthy is this agent right now?" It
does not answer "which way are they heading?" A counterparty can hold a high
score while deteriorating, or a mediocre score while climbing. Reflection reads
the journal, extracts that second-order signal, and consolidates it into a
durable credit memo that changes future decisions.

Two design commitments:

1. **Reflection only tightens.** A memo can cap a tier lower, never raise it. The
   score is the evidence; reflection adds caution, never optimism. This keeps the
   system fail-closed even as it grows more sophisticated.

2. **Free-tier only.** Sibyl's native `learn()` is gated to paid tier strings the
   hackathon grant does not set (verified in the SDK source), so it would raise
   for us and for a judge re-running the demo. This pass uses only journal reads
   and reference writes, which every tier has - so the reflection primitive works
   the same for everyone.

Pure functions here; persistence lives in the memory backend.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from .models import CounterpartyProfile, EventType, Tier, utcnow
from .scoring import score_profile

# Tier ordering, worst → best, for cap comparisons.
TIER_ORDER: list[Tier] = [Tier.UNKNOWN, Tier.BRONZE, Tier.SILVER, Tier.GOLD, Tier.PLATINUM]


def tier_rank(t: Tier) -> int:
    return TIER_ORDER.index(t)


def min_tier(a: Tier, b: Tier) -> Tier:
    return a if tier_rank(a) <= tier_rank(b) else b


class CreditMemo(BaseModel):
    """A consolidated, durable read on a counterparty's trajectory."""

    agent_id: str
    trend: str  # "improving" | "stable" | "deteriorating"
    volatility_hours: float
    recent_default: bool
    tier_cap: Tier | None = None
    summary: str = ""
    consolidated_events: int = 0
    updated_at: datetime = Field(default_factory=utcnow)

    def caps_below(self, tier: Tier) -> bool:
        return self.tier_cap is not None and tier_rank(self.tier_cap) < tier_rank(tier)


RECENT_WINDOW = timedelta(days=30)
# A trend needs a real gap to register, so noise does not flip the memo.
TREND_DELTA = 60.0  # points


def reflect(profile: CounterpartyProfile, now: datetime | None = None) -> CreditMemo:
    """Consolidate a counterparty's journal into a credit memo."""
    now = now or utcnow()
    events = sorted(profile.events, key=lambda e: e.occurred_at)

    # --- trend: score the older half vs the newer half of the history -----
    trend = "stable"
    if len(events) >= 4:
        mid = len(events) // 2
        older = CounterpartyProfile(agent_id=profile.agent_id)
        newer = CounterpartyProfile(agent_id=profile.agent_id)
        for e in events[:mid]:
            older.record(e)
        for e in events[mid:]:
            newer.record(e)
        # Evaluate both halves at the same instant so decay is not the signal.
        older_score = score_profile(older, now=now).score
        newer_score = score_profile(newer, now=now).score
        if newer_score - older_score >= TREND_DELTA:
            trend = "improving"
        elif older_score - newer_score >= TREND_DELTA:
            trend = "deteriorating"

    # --- volatility: dispersion of settlement timing ----------------------
    deltas = [
        e.settlement_delta_s / 3600.0
        for e in events
        if e.event_type == EventType.LOAN_REPAID and e.settlement_delta_s is not None
    ]
    volatility_hours = statistics.pstdev(deltas) if len(deltas) >= 2 else 0.0

    # --- recency of failure ----------------------------------------------
    recent_default = any(
        e.event_type == EventType.LOAN_DEFAULTED and (now - e.occurred_at) <= RECENT_WINDOW
        for e in events
    )

    # --- policy: reflection may only tighten -----------------------------
    tier_cap: Tier | None = None
    reasons: list[str] = []
    if recent_default:
        tier_cap = Tier.SILVER
        reasons.append("a default inside the last 30 days")
    if trend == "deteriorating":
        tier_cap = Tier.GOLD if tier_cap is None else min_tier(tier_cap, Tier.GOLD)
        reasons.append("a deteriorating trajectory across recent sessions")
    if volatility_hours >= 24.0 and recent_default:
        tier_cap = Tier.BRONZE if tier_cap is None else min_tier(tier_cap, Tier.BRONZE)
        reasons.append(f"erratic settlement timing (±{volatility_hours:.0f}h)")

    if reasons:
        summary = "Reflection caps credit at " + (tier_cap.value if tier_cap else "-") + ": " + "; ".join(reasons) + "."
    elif trend == "improving":
        summary = "Improving trajectory; no cap applied (reflection never loosens on optimism alone)."
    else:
        summary = "Stable trajectory; no policy override."

    return CreditMemo(
        agent_id=profile.agent_id,
        trend=trend,
        volatility_hours=round(volatility_hours, 2),
        recent_default=recent_default,
        tier_cap=tier_cap,
        summary=summary,
        consolidated_events=len(events),
        updated_at=now,
    )
