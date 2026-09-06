"""Tests for reflection - the consolidation pass that only ever tightens."""

from datetime import timedelta

from meritor.domain.models import CounterpartyProfile, CreditEvent, EventType, Tier, utcnow
from meritor.domain.scoring import COLLATERAL_RATIO, decide, score_profile
from meritor.domain.reflection import reflect, min_tier, tier_rank


def _p(events):
    p = CounterpartyProfile(agent_id="0xALPHA")
    for e in events:
        p.record(e)
    return p


def _clean(session, n, base_days, delta_h=-3):
    now = utcnow()
    out = []
    for i in range(n):
        out.append(CreditEvent(event_type=EventType.JOB_COMPLETED_ON_TIME, session_id=session,
                               occurred_at=now - timedelta(days=base_days - i), amount_usdc=40))
        out.append(CreditEvent(event_type=EventType.LOAN_REPAID, session_id=session,
                               occurred_at=now - timedelta(days=base_days - i), amount_usdc=120,
                               settlement_delta_s=delta_h * 3600))
    return out


def test_reflection_only_ever_tightens_a_tier():
    """A cap below the scored tier is applied; a cap above is ignored."""
    p = _p([*_clean("s1", 3, 40), *_clean("s2", 3, 20)])
    scored = score_profile(p).tier
    assert scored in (Tier.GOLD, Tier.PLATINUM)

    capped = decide(p, agent_id="0xALPHA", session_id="s3", requested_usdc=50,
                    tier_cap=Tier.SILVER)
    assert capped.tier is Tier.SILVER
    assert COLLATERAL_RATIO[capped.tier] > COLLATERAL_RATIO[scored]
    assert "Reflection capped" in capped.reason

    # A cap above the scored tier must not raise it.
    not_raised = decide(p, agent_id="0xALPHA", session_id="s3", requested_usdc=50,
                        tier_cap=Tier.PLATINUM)
    assert tier_rank(not_raised.tier) <= tier_rank(Tier.PLATINUM)
    assert not_raised.tier is scored


def test_recent_default_produces_a_cap():
    now = utcnow()
    p = _p([*_clean("s1", 3, 40), *_clean("s2", 3, 20)])
    p.record(CreditEvent(event_type=EventType.LOAN_DEFAULTED, session_id="s3",
                         occurred_at=now - timedelta(days=2), amount_usdc=300))
    memo = reflect(p)
    assert memo.recent_default is True
    assert memo.tier_cap is not None and tier_rank(memo.tier_cap) <= tier_rank(Tier.SILVER)


def test_deteriorating_trend_caps_at_gold():
    """Great early record, weak recent one: still scores well, but trend caps it."""
    now = utcnow()
    early = _clean("s1", 4, 60, delta_h=-6)   # early + on-time
    late = []
    for i in range(4):
        late.append(CreditEvent(event_type=EventType.JOB_COMPLETED_LATE, session_id="s2",
                                occurred_at=now - timedelta(days=8 - i), amount_usdc=40))
        late.append(CreditEvent(event_type=EventType.LOAN_REPAID, session_id="s2",
                                occurred_at=now - timedelta(days=8 - i), amount_usdc=120,
                                settlement_delta_s=20 * 3600))  # 20h late
    memo = reflect(_p([*early, *late]))
    assert memo.trend == "deteriorating"
    assert memo.tier_cap is Tier.GOLD or tier_rank(memo.tier_cap) < tier_rank(Tier.GOLD)


def test_improving_trend_never_loosens():
    now = utcnow()
    weak = []
    for i in range(3):
        weak.append(CreditEvent(event_type=EventType.JOB_COMPLETED_LATE, session_id="s1",
                                occurred_at=now - timedelta(days=40 - i), amount_usdc=40))
    strong = _clean("s2", 4, 10, delta_h=-6)
    memo = reflect(_p([*weak, *strong]))
    assert memo.trend == "improving"
    assert memo.tier_cap is None  # reflection adds caution, never optimism


def test_stable_history_has_no_cap():
    memo = reflect(_p(_clean("s1", 4, 30)))
    assert memo.trend == "stable" and memo.tier_cap is None


def test_min_tier_helper():
    assert min_tier(Tier.GOLD, Tier.SILVER) is Tier.SILVER
    assert min_tier(Tier.BRONZE, Tier.PLATINUM) is Tier.BRONZE
