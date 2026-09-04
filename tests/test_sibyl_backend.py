"""Tests against the real Sibyl Memory driver.

These exercise the actual substrate, not a mock — a fresh MemoryClient is opened
per backend instance, so a "recall" genuinely reads back from SQLite the way a
new process would. This is what a curious judge re-running the demo hits.
"""

from datetime import timedelta

import pytest

pytest.importorskip("sibyl_memory_client")

from meritor.domain.models import CreditEvent, EventType, Tier, utcnow
from meritor.domain.scoring import decide, score_profile
from meritor.memory.base import MemoryUnavailable
from meritor.memory.sibyl import SibylMemoryBackend


@pytest.fixture
def db(tmp_path):
    return tmp_path / "meritor-test.db"


def _fresh(db, tenant="t-test"):
    """A brand-new backend over the same file — stands in for a fresh process."""
    return SibylMemoryBackend(db_path=db, tenant_id=tenant)


def test_write_in_one_instance_recalls_in_another(db):
    a = _fresh(db)
    a.remember("0xALPHA", CreditEvent(
        event_type=EventType.LOAN_REPAID, session_id="s1",
        amount_usdc=50, settlement_delta_s=-3600))

    b = _fresh(db)  # a different instance, reading the same substrate
    profile = b.recall("0xALPHA")
    assert profile is not None
    assert profile.loans_repaid == 1


def test_recall_of_unknown_agent_is_none_not_error(db):
    assert _fresh(db).recall("0xNOBODY") is None


def test_deletion_test_collapses_to_zero_trust(db):
    a = _fresh(db)
    for i in range(4):
        a.remember("0xALPHA", CreditEvent(
            event_type=EventType.LOAN_REPAID, session_id=f"s{i}",
            occurred_at=utcnow() - timedelta(days=i * 7), amount_usdc=100,
            settlement_delta_s=-3600))

    before = _fresh(db).recall("0xALPHA")
    assert before is not None and before.loans_repaid == 4

    removed = _fresh(db).forget_all()
    assert removed == 1

    after = _fresh(db).recall("0xALPHA")
    assert after is None
    d = decide(after, agent_id="0xALPHA", session_id="s9", requested_usdc=50)
    assert not d.approved and d.tier is Tier.UNKNOWN and not d.memory_backed


def test_tier_is_mirrored_into_status_for_portfolio_sweeps(db):
    a = _fresh(db)
    for i in range(6):
        for etype in (EventType.JOB_COMPLETED_ON_TIME, EventType.LOAN_REPAID):
            a.remember("0xGOOD", CreditEvent(
                event_type=etype, session_id=f"s{i//2}",
                occurred_at=utcnow() - timedelta(days=(6 - i) * 5),
                amount_usdc=120, settlement_delta_s=-3600))
    tier = score_profile(_fresh(db).recall("0xGOOD")).tier
    assert "0xGOOD" in _fresh(db).by_tier(tier.value)


def test_time_travel_reconstructs_a_past_score(db):
    now = utcnow()
    a = _fresh(db)
    for i in range(6):
        a.remember("0xALPHA", CreditEvent(
            event_type=EventType.LOAN_REPAID, session_id=f"s{i//2}",
            occurred_at=now - timedelta(days=20 - i * 3), amount_usdc=120,
            settlement_delta_s=-3600))
        a.remember("0xALPHA", CreditEvent(
            event_type=EventType.JOB_COMPLETED_ON_TIME, session_id=f"s{i//2}",
            occurred_at=now - timedelta(days=20 - i * 3), amount_usdc=40))
    a.remember("0xALPHA", CreditEvent(
        event_type=EventType.LOAN_DEFAULTED, session_id="s9",
        occurred_at=now - timedelta(days=1), amount_usdc=500))

    b = _fresh(db)
    past = b.profile_as_of("0xALPHA", now - timedelta(days=3))
    assert past is not None
    assert past.loans_defaulted == 0, "the default was after this instant"

    then = score_profile(past, now=now - timedelta(days=3)).tier
    current = score_profile(b.recall("0xALPHA")).tier
    assert then is not current, "the default should have changed the tier"


def test_tenants_are_isolated(db):
    _fresh(db, tenant="lender-a").remember("0xALPHA", CreditEvent(
        event_type=EventType.LOAN_REPAID, session_id="s1", amount_usdc=50))
    # A different lender's namespace must not see it.
    assert _fresh(db, tenant="lender-b").recall("0xALPHA") is None


def test_journal_records_every_event(db):
    a = _fresh(db)
    a.remember("0xALPHA", CreditEvent(event_type=EventType.LOAN_REPAID, session_id="s1", amount_usdc=50))
    a.remember("0xALPHA", CreditEvent(event_type=EventType.JOB_COMPLETED_ON_TIME, session_id="s1", amount_usdc=40))
    entries = _fresh(db).journal(limit=100)
    assert len(entries) >= 2


def test_memo_survives_to_a_fresh_backend_instance(db):
    """A reflection memo written in one session caps credit in the next."""
    from datetime import timedelta
    from meritor.domain.models import utcnow
    from meritor.domain.reflection import reflect

    a = _fresh(db)
    now = utcnow()
    for i in range(6):
        a.remember("0xALPHA", CreditEvent(
            event_type=EventType.LOAN_REPAID, session_id=f"s{i//2}",
            occurred_at=now - timedelta(days=40 - i * 5), amount_usdc=120,
            settlement_delta_s=-3600))
    a.remember("0xALPHA", CreditEvent(
        event_type=EventType.LOAN_DEFAULTED, session_id="s9",
        occurred_at=now - timedelta(days=2), amount_usdc=300))

    memo = reflect(_fresh(db).recall("0xALPHA"))
    assert memo.tier_cap is not None
    _fresh(db).save_memo(memo)

    # A different instance loads the durable memo.
    loaded = _fresh(db).load_memo("0xALPHA")
    assert loaded is not None and loaded.tier_cap is memo.tier_cap
