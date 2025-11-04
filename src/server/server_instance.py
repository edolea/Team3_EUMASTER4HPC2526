"""Runtime representation for deployed server instances."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ServerStatus(Enum):
    """Lifecycle states for a server deployment."""

    SUBMITTED = "submitted"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ServerInstance:
    """Represents a single server deployment managed via SLURM."""

    def __init__(
        self,
        recipe_name: str,
        orchestrator_handle: str,
        command: str,
        *,
        ports: Optional[list[int]] = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.recipe_name = recipe_name
        self.command = command
        self.orchestrator_handle = orchestrator_handle
        self.status = ServerStatus.SUBMITTED
        self.ports = ports or []
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Lifecycle helpers
    # ---------------------------------------------------------------------
    def mark_starting(self) -> None:
        self.update_status(ServerStatus.STARTING)

    def mark_running(self) -> None:
        self.update_status(ServerStatus.RUNNING)

    def mark_completed(self) -> None:
        self.update_status(ServerStatus.COMPLETED)

    def mark_failed(self) -> None:
        self.update_status(ServerStatus.FAILED)

    def cancel(self) -> None:
        self.update_status(ServerStatus.CANCELED)

    def update_status(self, new_status: ServerStatus) -> None:
        self.status = new_status
        if new_status in {ServerStatus.COMPLETED, ServerStatus.FAILED, ServerStatus.CANCELED}:
            self.completed_at = datetime.now()

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "recipe_name": self.recipe_name,
            "status": self.status.value,
            "command": self.command,
            "ports": list(self.ports),
            "orchestrator_handle": self.orchestrator_handle,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "instance_id": self.id,
            "recipe_name": self.recipe_name,
            "status": self.status.value,
            "uptime_seconds": self._uptime_seconds(),
            "ports": list(self.ports),
            **self.metadata,
        }

    # ------------------------------------------------------------------
    def _uptime_seconds(self) -> float:
        end_time = self.completed_at or datetime.now()
        return (end_time - self.created_at).total_seconds()


__all__ = ["ServerInstance", "ServerStatus"]
