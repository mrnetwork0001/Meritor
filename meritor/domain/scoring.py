"""The credit scoring engine.

Pure functions over a CounterpartyProfile. No I/O, no network - which means
every point of a score is reproducible and auditable from the memory record
alone. That is the point: the score is a *function of recalled memory*, so
when memory is gone the score is not merely lower, it is undefined.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .models import (
    CounterpartyProfile,
    CreditDecision,
    EventType,
    ScoreBreakdown,
    Tier,
    utcnow,
)

# --- Weights (sum to 1000 points) ----------------------------------------

W_SLA = 350.0          # Did they finish the work, on time?
W_REPAYMENT = 300.0    # Did they pay back what they borrowed?
W_VELOCITY = 100.0     # How fast, relative to the deadline?
W_DISPUTES = 150.0     # Penalty pool, earned back by a clean record.
W_MATURITY = 100.0     # Tenure and volume - thin files stay thin.

# Half-life for behavioural decay. Good behaviour 90 days ago counts half as
# much as good behaviour today, so a profile has to stay earned.
DECAY_HALF_LIFE = timedelta(days=90)

# A counterparty with fewer than this many settled obligations cannot reach
# the uncollateralized tier no matter how clean the record is.
MIN_EVENTS_FOR_PLATINUM = 4

# Pseudo-observations of failure mixed into every ratio, so a thin file cannot
# claim a perfect record. Ratios are otherwise decay-invariant - 1/1 scores the
# same whether the observation is an hour or a decade old. Shrinking toward a
# pessimistic prior with the *decayed* evidence mass as the sample size makes
# stale evidence and scarce evidence fail the same way, which is correct: both
# mean we do not actually know much about this counterparty.
PRIOR_STRENGTH = 2.0


def _decay_weight(occurred_at: datetime, now: datetime) -> float:
    age = max((now - occurred_at).total_seconds(), 0.0)
    half_life = DECAY_HALF_LIFE.total_seconds()
    return 0.5 ** (age / half_life)


def _weighted_counts(profile: CounterpartyProfile, now: datetime) -> dict[EventType, float]:
    counts: dict[EventType, float] = {t: 0.0 for t in EventType}
    for event in profile.events:
        counts[event.event_type] += _decay_weight(event.occurred_at, now)
    return counts


def score_profile(profile: CounterpartyProfile, now: datetime | None = None) -> ScoreBreakdown:
    """Compute an explainable 0–1000 credit score from recalled memory."""
    now = now or utcnow()
    w = _weighted_counts(profile, now)
    components: dict[str, float] = {}
    rationale: list[str] = []

    # --- SLA completion -------------------------------------------------
    jobs = w[EventType.JOB_COMPLETED_ON_TIME] + w[EventType.JOB_COMPLETED_LATE] + w[EventType.JOB_FAILED]
    if jobs > 0:
        # Late delivery earns partial credit; outright failure earns none.
        quality_mass = w[EventType.JOB_COMPLETED_ON_TIME] + 0.4 * w[EventType.JOB_COMPLETED_LATE]
        quality = quality_mass / (jobs + PRIOR_STRENGTH)
        components["sla_completion"] = W_SLA * quality
        rationale.append(
            f"{profile.jobs_on_time}/{profile.jobs_total} ACP jobs delivered on time "
            f"({profile.jobs_late} late, {profile.jobs_failed} failed)"
        )
    else:
        components["sla_completion"] = 0.0
        rationale.append("no ACP job history on record")

    # --- Repayment reliability ------------------------------------------
    loans = w[EventType.LOAN_REPAID] + w[EventType.LOAN_DEFAULTED]
    if loans > 0:
        reliability = w[EventType.LOAN_REPAID] / (loans + PRIOR_STRENGTH)
        # A single default is disqualifying in a way a single late job is not.
        if w[EventType.LOAN_DEFAULTED] > 0:
            reliability *= 0.35
        components["repayment_reliability"] = W_REPAYMENT * reliability
        rationale.append(
            f"{profile.loans_repaid}/{profile.loans_settled} loans repaid "
            f"({profile.loans_defaulted} defaulted)"
        )
    else:
        components["repayment_reliability"] = 0.0
        rationale.append("no settled loan history on record")

    # --- Repayment velocity ---------------------------------------------
    deltas = [
        e.settlement_delta_s
        for e in profile.events
        if e.event_type == EventType.LOAN_REPAID and e.settlement_delta_s is not None
    ]
    if deltas:
        avg_delta = sum(deltas) / len(deltas)
        # Map [-1 day early, +1 day late] onto [1.0, 0.0], saturating outside.
        day = 86400.0
        velocity = max(0.0, min(1.0, 0.5 - (avg_delta / (2 * day))))
        components["repayment_velocity"] = W_VELOCITY * velocity
        if avg_delta < 0:
            rationale.append(f"repays {abs(avg_delta) / 3600:.1f}h ahead of deadline on average")
        else:
            rationale.append(f"repays {avg_delta / 3600:.1f}h past deadline on average")
    else:
        components["repayment_velocity"] = 0.0

    # --- Dispute record --------------------------------------------------
    # Asymmetric on purpose. A dispute resolved against you is hard evidence and
    # is charged at full weight immediately. A *clean* record, by contrast, is
    # only as meaningful as the volume of dealings behind it - never having been
    # disputed across two jobs says almost nothing, so the credit earns out with
    # the same evidence mass that drives every other component.
    clean_credit = W_DISPUTES * min(1.0, (jobs + loans) / 6.0)
    dispute_penalty = W_DISPUTES * (1.0 - math.exp(-1.2 * w[EventType.DISPUTE_RESOLVED_AGAINST]))
    open_penalty = 0.5 * W_DISPUTES if profile.disputes_open > 0 else 0.0
    components["dispute_record"] = clean_credit - dispute_penalty - open_penalty
    if profile.disputes_against:
        rationale.append(f"{profile.disputes_against} dispute(s) resolved against this agent")
    if profile.disputes_open:
        rationale.append(f"{profile.disputes_open} dispute(s) currently open - credit frozen")

    # --- Maturity --------------------------------------------------------
    settled_mass = jobs + loans
    depth = min(1.0, math.log1p(settled_mass) / math.log1p(12))
    volume = min(1.0, math.log1p(profile.total_volume_usdc) / math.log1p(5000))
    tenure = min(1.0, len(profile.sessions_seen) / 4.0)
    components["maturity"] = W_MATURITY * (0.4 * depth + 0.3 * volume + 0.3 * tenure)
    rationale.append(
        f"observed across {len(profile.sessions_seen)} session(s), "
        f"${profile.total_volume_usdc:,.0f} lifetime volume"
    )

    score = max(0.0, min(1000.0, sum(components.values())))
    tier = tier_for(score, profile)

    return ScoreBreakdown(
        agent_id=profile.agent_id,
        score=score,
        tier=tier,
        components=components,
        rationale=rationale,
        evidence_events=len(profile.events),
        sessions_observed=len(profile.sessions_seen),
        computed_at=now,
    )


# --- Tier policy ----------------------------------------------------------

TIER_THRESHOLDS: list[tuple[float, Tier]] = [
    (820.0, Tier.PLATINUM),
    (620.0, Tier.GOLD),
    (420.0, Tier.SILVER),
    (200.0, Tier.BRONZE),
]

# Collateral required as a fraction of the requested principal.
COLLATERAL_RATIO: dict[Tier, float] = {
    Tier.UNKNOWN: 1.50,
    Tier.BRONZE: 1.20,
    Tier.SILVER: 0.75,
    Tier.GOLD: 0.25,
    Tier.PLATINUM: 0.00,
}

# Hard exposure ceiling per tier, in USDC.
MAX_PRINCIPAL_USDC: dict[Tier, float] = {
    Tier.UNKNOWN: 0.0,
    Tier.BRONZE: 100.0,
    Tier.SILVER: 500.0,
    Tier.GOLD: 2_000.0,
    Tier.PLATINUM: 10_000.0,
}


def tier_for(score: float, profile: CounterpartyProfile) -> Tier:
    tier = Tier.UNKNOWN
    for threshold, candidate in TIER_THRESHOLDS:
        if score >= threshold:
            tier = candidate
            break

    # Guardrails: uncollateralized credit requires a track record that spans
    # sessions. One good session is not a credit history.
    if tier is Tier.PLATINUM:
        settled = profile.jobs_total + profile.loans_settled
        if settled < MIN_EVENTS_FOR_PLATINUM or not profile.is_returning:
            tier = Tier.GOLD

    if profile.disputes_open > 0 and tier in (Tier.PLATINUM, Tier.GOLD):
        tier = Tier.SILVER

    return tier


def decide(
    profile: CounterpartyProfile | None,
    *,
    agent_id: str,
    session_id: str,
    requested_usdc: float,
    memory_available: bool = True,
    tier_cap: "Tier | None" = None,
) -> CreditDecision:
    """Turn recalled memory into a lending decision.

    `profile is None` means Sibyl Memory returned nothing for this agent -
    either a genuinely new counterparty, or the memory layer is gone. Both
    collapse to the same fail-closed outcome: no uncollateralized credit.
    """
    if not memory_available:
        return CreditDecision(
            agent_id=agent_id,
            session_id=session_id,
            requested_usdc=requested_usdc,
            approved=False,
            approved_usdc=0.0,
            collateral_required_usdc=requested_usdc * COLLATERAL_RATIO[Tier.UNKNOWN],
            collateral_ratio=COLLATERAL_RATIO[Tier.UNKNOWN],
            tier=Tier.UNKNOWN,
            score=0.0,
            reason=(
                "MEMORY UNAVAILABLE - Meritor cannot recall this counterparty's "
                "credit history and has no basis to price risk. Falling back to "
                "0-trust: uncollateralized credit denied."
            ),
            memory_backed=False,
        )

    if profile is None or not profile.events:
        return CreditDecision(
            agent_id=agent_id,
            session_id=session_id,
            requested_usdc=requested_usdc,
            approved=False,
            approved_usdc=0.0,
            collateral_required_usdc=requested_usdc * COLLATERAL_RATIO[Tier.UNKNOWN],
            collateral_ratio=COLLATERAL_RATIO[Tier.UNKNOWN],
            tier=Tier.UNKNOWN,
            score=0.0,
            reason=(
                "No credit memory for this counterparty. Unknown agents must "
                f"post {COLLATERAL_RATIO[Tier.UNKNOWN]:.0%} collateral; "
                "uncollateralized request denied."
            ),
            memory_backed=False,
        )

    breakdown = score_profile(profile)
    tier = breakdown.tier
    cap_note = ""
    if tier_cap is not None:
        from .reflection import min_tier

        capped = min_tier(tier, tier_cap)
        if capped is not tier:
            cap_note = (
                f" Reflection capped {tier.value}→{capped.value} on a "
                f"consolidated risk trend."
            )
            tier = capped
    ratio = COLLATERAL_RATIO[tier]
    ceiling = MAX_PRINCIPAL_USDC[tier]
    approved_usdc = min(requested_usdc, ceiling)
    approved = approved_usdc > 0

    if not approved:
        reason = f"Tier {tier.value} carries a ${ceiling:,.0f} exposure ceiling - request denied."
    elif approved_usdc < requested_usdc:
        reason = (
            f"Recalled {breakdown.evidence_events} credit events across "
            f"{breakdown.sessions_observed} sessions → {tier.value} "
            f"({breakdown.score:.0f}/1000). Approving ${approved_usdc:,.2f} of "
            f"${requested_usdc:,.2f} at {ratio:.0%} collateral (tier ceiling)."
        )
    else:
        reason = (
            f"Recalled {breakdown.evidence_events} credit events across "
            f"{breakdown.sessions_observed} sessions → {tier.value} "
            f"({breakdown.score:.0f}/1000). Approving ${approved_usdc:,.2f} at "
            f"{ratio:.0%} collateral."
        )

    return CreditDecision(
        agent_id=agent_id,
        session_id=session_id,
        requested_usdc=requested_usdc,
        approved=approved,
        approved_usdc=approved_usdc,
        collateral_required_usdc=approved_usdc * ratio,
        collateral_ratio=ratio,
        tier=tier,
        score=breakdown.score,
        reason=reason + cap_note,
        memory_backed=True,
        breakdown=breakdown,
    )
