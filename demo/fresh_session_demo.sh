#!/usr/bin/env bash
# Meritor — the fresh-session recall beat.
#
# Every command below is a SEPARATE process. Nothing survives in RAM between
# them. Anything Meritor knows in a later block, it learned by reading the
# memory layer back. MERITOR_SESSION_ID marks the logical session boundary so
# the credit record's session count is explicit and auditable.
set -euo pipefail

PY="${PY:-.venv/bin/python}"
ALPHA="${ALPHA:-0xALPHA}"
BETA="${BETA:-0xBETA}"
# The mandatory substrate. The deletion beat must erase Sibyl Memory itself,
# not a stand-in JSON file, or the experiment proves nothing.
export MEMORY_DRIVER="${MEMORY_DRIVER:-sibyl}"
export SIBYL_MEMORY_DB="${SIBYL_MEMORY_DB:-.meritor/demo.db}"
export SIBYL_TENANT_ID="${SIBYL_TENANT_ID:-meritor-demo}"

step() { printf '\n\n\033[1;36m━━━ %s ━━━\033[0m\n\n' "$1"; sleep "${PAUSE:-0}"; }

rm -f "$SIBYL_MEMORY_DB"

step "SETUP · replay 0xALPHA's prior operating history (backdated, labelled)"
$PY -m meritor.cli seed "$ALPHA" --sessions 3 --per-session 4

step "STACK · Virtuals ACP — a completed job becomes a credit event"
MERITOR_SESSION_ID=sess_seed $PY -m meritor.cli acp-job "$ALPHA" \
  --offering risk-audit --budget 10 ${ACP_FLAGS:---mock}

step "SESSION A · 0xBETA, never seen before, asks for \$50 uncollateralized"
MERITOR_SESSION_ID=sess_A $PY -m meritor.cli request "$BETA" 50 || true

step "SESSION A · 0xALPHA asks for the same \$50 — and Base settles it"
# --settle releases USDC on Base against the recalled tier. With no funded
# wallet this prints DRY_RUN (no fabricated hash); fund .env's address on Base
# Sepolia and set SETTLE_TO to broadcast a real, on-Basescan transaction.
MERITOR_SESSION_ID=sess_A $PY -m meritor.cli request "$ALPHA" 50 \
  ${SETTLE_TO:+--settle "$SETTLE_TO"} || true

step "SESSION A · 0xBETA does the work anyway, over-collateralized"
MERITOR_SESSION_ID=sess_A $PY -m meritor.cli work  "$BETA" --outcome on_time --amount 40 --acp-job-id acp_beta_001
MERITOR_SESSION_ID=sess_A $PY -m meritor.cli repay "$BETA" 50 --early-hours 3 --tx-hash 0xbeta001

step "SESSION B · FRESH PROCESS, NEW SESSION · 0xBETA returns"
MERITOR_SESSION_ID=sess_B $PY -m meritor.cli request "$BETA" 50 || true

step "SESSION B · what Meritor recalled in order to price that"
MERITOR_SESSION_ID=sess_B $PY -m meritor.cli explain "$BETA"

step "SESSION B · time-travel: what did Meritor know before today?"
MERITOR_SESSION_ID=sess_B $PY -m meritor.cli as-of "$ALPHA" --days-ago 10

step "STACK · Base — publish 0xALPHA's recalled tier as an EAS attestation"
# --dry-run prints the exact payload; fund .env's wallet and drop --dry-run to
# broadcast a real attestation viewable on base(-sepolia).easscan.org.
MERITOR_SESSION_ID=sess_B $PY -m meritor.cli attest "$ALPHA" ${ATTEST_FLAGS:---dry-run}

step "THE DELETION TEST · erase Sibyl Memory itself"
$PY -m meritor.cli wipe --yes

step "SESSION C · FRESH PROCESS · 0xALPHA repeats the identical request"
MERITOR_SESSION_ID=sess_C $PY -m meritor.cli request "$ALPHA" 50 || true

printf '\n\n\033[1;33m  Same agent. Same request. The only variable was memory.\033[0m\n'
printf '\033[1;33m  PLATINUM / 0%% collateral  →  UNKNOWN / denied.\033[0m\n\n'
