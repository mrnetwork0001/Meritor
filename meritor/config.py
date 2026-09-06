"""Runtime configuration.

One rule governs this module: there is no automatic fallback from the real
memory backend to a local one. If Sibyl Memory is configured and unreachable,
Meritor fails closed rather than silently substituting a backend that would
make the credit engine look like it still works.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

MemoryDriver = Literal["sibyl", "local"]


@dataclass(frozen=True)
class Settings:
    # --- Memory (mandatory, load-bearing) --------------------------------
    # Sibyl Memory is a local SQLite substrate, not a hosted API. There is no
    # key and no endpoint to configure - only where the file lives and which
    # tenant partition inside it Meritor owns.
    memory_driver: MemoryDriver
    sibyl_db_path: Path
    sibyl_tenant_id: str
    local_memory_path: Path

    # --- Base (partner stack) --------------------------------------------
    base_rpc_url: str | None
    base_chain_id: int
    base_private_key: str | None
    usdc_address: str | None

    # --- Virtuals (partner stack) ----------------------------------------
    virtuals_api_key: str | None
    virtuals_agent_id: str | None

    env: str

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def require_sibyl(self) -> None:
        """Refuse to start a production run on anything but the real substrate."""
        if self.memory_driver != "sibyl":
            raise RuntimeError(
                f"MERITOR_ENV=production requires MEMORY_DRIVER=sibyl, got "
                f"{self.memory_driver!r}. The local driver is a development "
                f"convenience and must never back a real credit decision."
            )


def load_settings() -> Settings:
    env = os.getenv("MERITOR_ENV", "development")
    driver: MemoryDriver = os.getenv("MEMORY_DRIVER", "local")  # type: ignore[assignment]
    if driver not in ("sibyl", "local"):
        raise RuntimeError(f"MEMORY_DRIVER must be 'sibyl' or 'local', got {driver!r}")

    settings = Settings(
        memory_driver=driver,
        sibyl_db_path=Path(os.getenv("SIBYL_MEMORY_DB", "~/.sibyl-memory/meritor.db")),
        sibyl_tenant_id=os.getenv("SIBYL_TENANT_ID", "meritor-credit"),
        local_memory_path=Path(os.getenv("LOCAL_MEMORY_PATH", ".meritor/memory.json")),
        base_rpc_url=os.getenv("BASE_RPC_URL"),
        base_chain_id=int(os.getenv("BASE_CHAIN_ID", "84532")),  # Base Sepolia by default
        base_private_key=os.getenv("BASE_PRIVATE_KEY"),
        usdc_address=os.getenv("USDC_ADDRESS"),
        virtuals_api_key=os.getenv("VIRTUALS_API_KEY"),
        virtuals_agent_id=os.getenv("VIRTUALS_AGENT_ID"),
        env=env,
    )
    if settings.is_production:
        settings.require_sibyl()
    return settings
