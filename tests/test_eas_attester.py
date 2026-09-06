"""Tests for the EAS attester - encoding, honest dry-run, no fabricated UID."""

from meritor.agents.eas_attester import (
    EASAttester, Attestation, AttestStatus, compute_schema_uid,
    SCHEMA_STRING, SCHEMA_TYPES, EAS_ADDRESS, SCHEMA_REGISTRY_ADDRESS,
)


def test_schema_uid_is_deterministic():
    a, b = compute_schema_uid(), compute_schema_uid()
    assert a == b and a.startswith("0x") and len(a) == 66


def test_predeploy_addresses_are_the_op_stack_eas():
    assert EAS_ADDRESS == "0x4200000000000000000000000000000000000021"
    assert SCHEMA_REGISTRY_ADDRESS == "0x4200000000000000000000000000000000000020"


def test_schema_field_count_matches_types():
    assert len(SCHEMA_STRING.split(",")) == len(SCHEMA_TYPES) == 6


def test_encoding_roundtrips():
    from eth_abi import decode
    att = EASAttester(chain_id=84532)
    data = att._encode("0xALPHA", 845, "PLATINUM", 24, 3, 1725000000)
    values = decode(SCHEMA_TYPES, data)
    assert values[0] == "0xALPHA" and values[1] == 845 and values[2] == "PLATINUM"
    assert values[3] == 24 and values[4] == 3 and values[5] == 1725000000


def test_unfunded_attest_is_dry_run_not_a_fake_uid():
    att = EASAttester(chain_id=84532)  # no private key
    r = att.attest_credit("0xALPHA", 845, "PLATINUM", 24, 3, 1725000000)
    assert r.status is AttestStatus.DRY_RUN
    assert r.uid is None and not r.is_onchain
    assert "BASE_PRIVATE_KEY" in r.detail


def test_dry_run_carries_the_exact_payload():
    att = EASAttester(chain_id=84532)
    r = att.attest_credit("0xBETA", 361, "BRONZE", 3, 2, 1725000000, dry_run=True)
    assert r.payload == {
        "agentId": "0xBETA", "score": 361, "tier": "BRONZE",
        "evidenceCount": 3, "sessions": 2, "assessedAt": 1725000000,
    }
    assert not r.is_onchain
