"""A file-backed memory driver for development and CI.

DEVELOPMENT ONLY. This exists so the credit engine can be exercised without
Sibyl credentials - not as a fallback. Nothing in Meritor ever switches to
this driver automatically; selecting it is an explicit MEMORY_DRIVER=local
choice, and `Settings.require_sibyl()` blocks it in production.

The deletion test runs against whichever driver is configured, so running the
demo on this driver demonstrates the same failure mode it would on Sibyl.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.models import CounterpartyProfile, CreditEvent
from .base import MemoryBackend, MemoryUnavailable


class LocalFileBackend(MemoryBackend):
    def __init__(self, path: Path, namespace: str = "meritor-credit") -> None:
        self._path = Path(path)
        self._namespace = namespace

    @property
    def name(self) -> str:
        return f"local-file[{self._path}]"

    # --- storage ---------------------------------------------------------

    def _read_all(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        try:
            blob = json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise MemoryUnavailable(f"local memory at {self._path} is unreadable: {exc}") from exc
        return blob.get(self._namespace, {})

    def _write_all(self, profiles: dict[str, dict]) -> None:
        blob: dict = {}
        if self._path.exists():
            try:
                blob = json.loads(self._path.read_text())
            except (OSError, json.JSONDecodeError):
                blob = {}
        blob[self._namespace] = profiles
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(blob, indent=2, default=str))

    # --- MemoryBackend ---------------------------------------------------

    def health(self) -> bool:
        try:
            self._read_all()
            return True
        except MemoryUnavailable:
            return False

    def recall(self, agent_id: str) -> CounterpartyProfile | None:
        raw = self._read_all().get(agent_id)
        return CounterpartyProfile.model_validate(raw) if raw else None

    def remember(self, agent_id: str, event: CreditEvent) -> CounterpartyProfile:
        profiles = self._read_all()
        raw = profiles.get(agent_id)
        profile = (
            CounterpartyProfile.model_validate(raw)
            if raw
            else CounterpartyProfile(agent_id=agent_id)
        )
        profile.record(event)
        profiles[agent_id] = json.loads(profile.model_dump_json())
        self._write_all(profiles)
        return profile

    def forget(self, agent_id: str) -> None:
        profiles = self._read_all()
        profiles.pop(agent_id, None)
        self._write_all(profiles)

    def forget_all(self) -> int:
        n = len(self._read_all())
        self._write_all({})
        return n

    def known_agents(self) -> list[str]:
        return sorted(self._read_all())

    # --- Reflection memos -------------------------------------------------

    def _memo_path_key(self) -> str:
        return f"__memos__::{self._namespace}"

    def save_memo(self, memo) -> None:
        blob = {}
        if self._path.exists():
            try:
                blob = json.loads(self._path.read_text())
            except (OSError, json.JSONDecodeError):
                blob = {}
        memos = blob.get(self._memo_path_key(), {})
        memos[memo.agent_id] = json.loads(memo.model_dump_json())
        blob[self._memo_path_key()] = memos
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(blob, indent=2, default=str))

    def load_memo(self, agent_id: str):
        from ..domain.reflection import CreditMemo

        if not self._path.exists():
            return None
        try:
            blob = json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        raw = blob.get(self._memo_path_key(), {}).get(agent_id)
        return CreditMemo.model_validate(raw) if raw else None
