"""Recipe definition for server deployments."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ServerRecipe:
    """Represents a server deployment recipe loaded from YAML."""

    def __init__(
        self,
        name: str,
        service: Dict[str, Any],
        *,
        orchestration: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> None:
        self.name = name
        self.service = service or {}
        self.orchestration = orchestration or {}
        self.description = description

    # ------------------------------------------------------------------
    def validate(self) -> None:
        if not self.name:
            raise ValueError("Recipe name is required")

        if not self.service:
            raise ValueError("service definition is required")

        command = self.service.get("command")
        if not command or not isinstance(command, str):
            raise ValueError("service.command must be a non-empty string")

        ports = self.service.get("ports", [])
        if any(p <= 0 or p > 65535 for p in ports):
            raise ValueError("service.ports must contain valid TCP port numbers")

    # ------------------------------------------------------------------
    @property
    def resources(self) -> Dict[str, Any]:
        return self.orchestration.get("resources", {})

    @property
    def env(self) -> Dict[str, str]:
        return self.service.get("env", {})

    @property
    def working_directory(self) -> Optional[str]:
        return self.service.get("working_dir")

    @property
    def ports(self) -> list[int]:
        return list(self.service.get("ports", []))

    # ------------------------------------------------------------------
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "ServerRecipe":
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Recipe file not found: {yaml_path}")

        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        recipe = cls(
            name=data.get("name"),
            service=data.get("service", {}),
            orchestration=data.get("orchestration"),
            description=data.get("description"),
        )

        recipe.validate()
        return recipe


__all__ = ["ServerRecipe"]
