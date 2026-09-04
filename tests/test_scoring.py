"""Tests for the credit engine — especially the fail-closed guarantees."""

from datetime import timedelta

from meritor.domain.models import CounterpartyProfile, CreditEvent, EventType, Tier, utcnow
from meritor.domain.scoring import COLLATERAL_RATIO, decide, score_profile


def _profile(agent_id="0xALPHA", sessions=("s1",), events=()):
    p = CounterpartyProfile(agent_id=agent_id)
    for e in events:
        p.record(e)
    return p


def _good_history(session_id: str, n: int = 3):
    now = utcnow()
    out = []
    for i in range(n):
        out.append(
            CreditEvent(
                event_type=EventType.JOB_COMPLETED_ON_TIME,
                session_id=session_id,
                occurred_at=now - timedelta(days=i),
                amount_usdc=25.0,
            )
        )
        out.append(
            CreditEvent(
                event_type=EventType.LOAN_REPAID,
                session_id=session_id,
                occurred_at=now - timedelta(days=i),
                amount_usdc=50.0,
                settlement_delta_s=-7200.0,  # two hours early
            )
        )
    return out


def test_no_memory_denies_uncollateralized_credit():
    d = decide(None, agent_id="0xALPHA", session_id="s2", requested_usdc=50.0, memory_available=True)
    assert d.approved is False
    assert d.tier is Tier.UNKNOWN
    assert d.memory_backed is False
    assert d.collateral_ratio == COLLATERAL_RATIO[Tier.UNKNOWN] == 1.50


def test_memory_outage_is_not_mistaken_for_a_new_agent():
    """The deletion test: an unreachable backend must never read as a clean slate."""
    d = decide(None, agent_id="0xALPHA", session_id="s2", requested_usdc=50.0, memory_available=False)
    assert d.approved is False
    assert d.memory_backed is False
    assert "MEMORY UNAVAILABLE" in d.reason


def test_uncollateralized_credit_is_never_granted_without_memory():
    """The invariant that makes memory load-bearing rather than decorative."""
    for available in (True, False):
        d = decide(None, agent_id="0xX", session_id="s", requested_usdc=1000.0, memory_available=available)
        assert not (d.approved and d.collateral_ratio == 0.0)
        assert d.memory_backed is False


def test_single_session_history_cannot_reach_platinum():
    """One good session is not a credit history."""
    p = _profile(events=_good_history("s1", n=6))
    b = score_profile(p)
    assert b.tier is not Tier.PLATINUM, "uncollateralized tier must require cross-session evidence"


def test_cross_session_history_unlocks_lower_collateral():
    """The headline beat: memory written in session 1 changes the session 2 decision."""
    p = _profile(events=[*_good_history("s1", n=3), *_good_history("s2", n=3)])
    assert p.is_returning
    b = score_profile(p)
    assert b.tier in (Tier.GOLD, Tier.PLATINUM), b.explain()

    d = decide(p, agent_id=p.agent_id, session_id="s3", requested_usdc=50.0)
    assert d.approved
    assert d.memory_backed
    assert d.collateral_ratio < COLLATERAL_RATIO[Tier.UNKNOWN]


def test_default_craters_the_score():
    """A default must collapse the repayment component and cost a whole tier."""
    p = _profile(events=[*_good_history("s1", 3), *_good_history("s2", 3)])
    clean = score_profile(p)

    p.record(CreditEvent(event_type=EventType.LOAN_DEFAULTED, session_id="s3", amount_usdc=50.0))
    after = score_profile(p)

    assert after.components["repayment_reliability"] < 0.4 * clean.components["repayment_reliability"]
    assert after.score < clean.score
    # A tier demotion is what the borrower actually feels: collateral goes up.
    assert COLLATERAL_RATIO[after.tier] > COLLATERAL_RATIO[clean.tier]


def test_open_dispute_freezes_the_top_tiers():
    p = _profile(events=[*_good_history("s1", 3), *_good_history("s2", 3)])
    p.record(CreditEvent(event_type=EventType.DISPUTE_OPENED, session_id="s3"))
    b = score_profile(p)
    assert b.tier not in (Tier.PLATINUM, Tier.GOLD)


def test_score_is_explainable():
    p = _profile(events=_good_history("s1", 2))
    text = score_profile(p).explain()
    assert "sla_completion" in text and "/1000" in text


def test_decay_makes_stale_good_behaviour_worth_less():
    now = utcnow()
    fresh = _profile(events=[
        CreditEvent(event_type=EventType.LOAN_REPAID, session_id="s1", occurred_at=now, amount_usdc=50.0),
    ])
    stale = _profile(events=[
        CreditEvent(event_type=EventType.LOAN_REPAID, session_id="s1",
                    occurred_at=now - timedelta(days=365), amount_usdc=50.0),
    ])
    assert score_profile(stale, now=now).score < score_profile(fresh, now=now).score


def test_clean_record_credit_earns_out_with_evidence():
    """Never having been disputed across two jobs says almost nothing."""
    thin = _profile(events=_good_history("s1", n=1))
    thick = _profile(events=[*_good_history("s1", 3), *_good_history("s2", 3)])
    assert thin.disputes_against == thick.disputes_against == 0
    assert score_profile(thin).components["dispute_record"] < \
        score_profile(thick).components["dispute_record"]


def test_dispute_penalty_applies_at_full_weight_immediately():
    """Penalties are hard evidence and must not be shrunk toward neutral."""
    clean = _profile(events=[*_good_history("s1", 3), *_good_history("s2", 3)])
    dirty = _profile(events=[*_good_history("s1", 3), *_good_history("s2", 3)])
    dirty.record(CreditEvent(event_type=EventType.DISPUTE_RESOLVED_AGAINST, session_id="s2"))
    drop = (score_profile(clean).components["dispute_record"]
            - score_profile(dirty).components["dispute_record"])
    assert drop > 100.0, f"one adverse dispute only cost {drop:.0f} points"


def test_thin_file_starts_expensive():
    """A counterparty with a two-event history must not get cheap credit."""
    thin = _profile(events=_good_history("s1", n=1))
    d = decide(thin, agent_id=thin.agent_id, session_id="s1", requested_usdc=500.0)
    assert d.collateral_ratio >= 1.0, "thin files must be over-collateralized"
