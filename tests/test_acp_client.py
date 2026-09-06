"""Tests for the Virtuals ACP driver — the credit-event mapping, mock lifecycle."""

from meritor.agents.acp_client import ACPClient, JobPhase, JobResult, PHASE_TO_EVENT
from meritor.domain.models import EventType


def test_completed_job_becomes_an_on_time_credit_event():
    r = JobResult(job_id="j1", phase=JobPhase.COMPLETED, amount_usdc=25.0)
    ev = r.to_credit_event("s1")
    assert ev is not None and ev.event_type is EventType.JOB_COMPLETED_ON_TIME
    assert ev.acp_job_id == "j1" and ev.amount_usdc == 25.0


def test_late_flag_downgrades_the_event():
    r = JobResult(job_id="j1", phase=JobPhase.COMPLETED, amount_usdc=25.0)
    ev = r.to_credit_event("s1", late=True)
    assert ev.event_type is EventType.JOB_COMPLETED_LATE


def test_rejected_and_expired_jobs_are_failures():
    for phase in (JobPhase.REJECTED, JobPhase.EXPIRED):
        ev = JobResult(job_id="j", phase=phase).to_credit_event("s1")
        assert ev is not None and ev.event_type is EventType.JOB_FAILED


def test_pending_jobs_produce_no_credit_event():
    for phase in (JobPhase.OPEN, JobPhase.BUDGET_SET, JobPhase.FUNDED, JobPhase.SUBMITTED):
        assert JobResult(job_id="j", phase=phase).to_credit_event("s1") is None


def test_mock_dispatch_completes_and_maps_to_a_credit_event():
    client = ACPClient(mock=True)
    ok, _ = client.available()
    assert ok
    providers = client.browse("risk audit")
    assert providers and providers[0]["id"]
    job = client.dispatch(providers[0]["id"], "risk-audit", 10.0)
    assert job.phase is JobPhase.COMPLETED
    ev = job.to_credit_event("s1")
    assert ev.event_type is EventType.JOB_COMPLETED_ON_TIME
    assert ev.amount_usdc == 10.0


def test_phase_mapping_is_total():
    """Every phase must map to an event or explicit None — no KeyError at runtime."""
    for phase in JobPhase:
        assert phase in PHASE_TO_EVENT


def test_whoami_mock_returns_registered_identity():
    from meritor.agents.acp_client import ACPClient, REGISTERED_AGENT
    who = ACPClient(mock=True).whoami()
    assert who["acp_agent_id"] == REGISTERED_AGENT["acp_agent_id"]
    assert who["erc8004_id_base"] == 84921
