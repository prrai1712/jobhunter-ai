"""System service — state machine management for the entire platform."""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repositories.other_repositories import SystemSettingsRepository, WorkerStatusRepository


class SystemState(str, enum.Enum):
    """Valid system states with allowed transitions."""

    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    MAINTENANCE = "maintenance"


# Valid state transitions
ALLOWED_TRANSITIONS: dict[SystemState, set[SystemState]] = {
    SystemState.STOPPED: {SystemState.RUNNING, SystemState.MAINTENANCE},
    SystemState.RUNNING: {SystemState.PAUSED, SystemState.STOPPED, SystemState.MAINTENANCE},
    SystemState.PAUSED: {SystemState.RUNNING, SystemState.STOPPED},
    SystemState.MAINTENANCE: {SystemState.STOPPED, SystemState.RUNNING},
}


class SystemService:
    """Manages the global system state and worker health."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings_repo = SystemSettingsRepository(session)
        self.worker_repo = WorkerStatusRepository(session)

    async def get_state(self) -> SystemState:
        """Get current system state."""
        value = await self.settings_repo.get_setting("system_state")
        if value is None:
            return SystemState.STOPPED
        state_str = value.get("state", "stopped") if isinstance(value, dict) else str(value)
        try:
            return SystemState(state_str)
        except ValueError:
            return SystemState.STOPPED

    async def set_state(self, new_state: SystemState, updated_by: str = "system") -> bool:
        """Set system state if the transition is valid."""
        current = await self.get_state()
        if new_state not in ALLOWED_TRANSITIONS.get(current, set()):
            return False
        await self.settings_repo.set_setting(
            "system_state",
            {"state": new_state.value},
            description=f"System state: {new_state.value}",
            updated_by=updated_by,
        )
        return True

    async def force_state(self, new_state: SystemState, updated_by: str = "system") -> None:
        """Force set state regardless of transition rules (for initialization/recovery)."""
        await self.settings_repo.set_setting(
            "system_state",
            {"state": new_state.value},
            description=f"System state force-set to {new_state.value}",
            updated_by=updated_by,
        )

    async def is_running(self) -> bool:
        """Check if system is in running state."""
        return (await self.get_state()) == SystemState.RUNNING

    async def is_paused(self) -> bool:
        """Check if applications are paused."""
        return (await self.get_state()) == SystemState.PAUSED

    async def can_discover(self) -> bool:
        """Check if job discovery should run (runs in RUNNING and PAUSED states)."""
        state = await self.get_state()
        return state in (SystemState.RUNNING, SystemState.PAUSED)

    async def can_apply(self) -> bool:
        """Check if auto-apply should run (only in RUNNING state)."""
        return await self.is_running()

    async def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status for the /system_status command."""
        state = await self.get_state()
        workers = await self.worker_repo.get_all_workers()

        return {
            "state": state.value,
            "workers": [
                {
                    "name": w.worker_name,
                    "status": w.status,
                    "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
                    "last_run": w.last_run_at.isoformat() if w.last_run_at else None,
                    "next_run": w.next_run_at.isoformat() if w.next_run_at else None,
                    "error": w.error_message,
                }
                for w in workers
            ],
        }

    async def update_worker_heartbeat(self, worker_name: str, **kwargs: Any) -> None:
        """Update a worker's heartbeat and status."""
        await self.worker_repo.upsert_status(worker_name, status="running", **kwargs)

    async def set_worker_error(self, worker_name: str, error: str) -> None:
        """Mark a worker as errored."""
        await self.worker_repo.upsert_status(
            worker_name, status="error", error_message=error
        )
