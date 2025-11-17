from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

class MonitorStatus(str, Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"

@dataclass
class MonitorRecipe:
    name: str
    description: str = ""
    scrape_interval: str = "5s"
    scrape_timeout: str = "4s"
    target_services: List[str] = field(default_factory=list)
    extra_config: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_yaml(path: str) -> "MonitorRecipe":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Recipe file not found: {path}")
        if yaml is None:
            raise RuntimeError("PyYAML is required to load recipe YAML files.")
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        name = data.get("name") or p.stem
        description = data.get("description", "")
        scrape_interval = data.get("scrape_interval", "5s")
        scrape_timeout = data.get("scrape_timeout", "4s")
        target_services = list(data.get("targets", []))
        extra_config = dict(data.get("extra_config", {}))
        return MonitorRecipe(
            name=name,
            description=description,
            scrape_interval=scrape_interval,
            scrape_timeout=scrape_timeout,
            target_services=target_services,
            extra_config=extra_config,
        )

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Recipe.name must not be empty")
        for attr in ("scrape_interval", "scrape_timeout"):
            val = getattr(self, attr)
            if not isinstance(val, str) or not val.endswith(("s", "m", "h")):
                raise ValueError(f"{attr} should be a duration string like '5s', '1m'")
        if not isinstance(self.target_services, list):
            raise ValueError("targets must be a list of host:port strings")

    def to_prometheus_config(self, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        # Minimal Prometheus scrape config
        t = targets if targets is not None else self.target_services
        return {
            "global": {
                "scrape_interval": self.scrape_interval,
                "scrape_timeout": self.scrape_timeout,
            },
            "scrape_configs": [
                {
                    "job_name": self.name,
                    "static_configs": [{"targets": t}],
                }
            ],
            **(self.extra_config or {}),
        }

@dataclass
class MonitorInstance:
    id: str
    recipe: MonitorRecipe
    status: MonitorStatus
    created_at_iso: str
    prometheus_url: Optional[str] = None
    grafana_url: Optional[str] = None
    targets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "recipe": {
                "name": self.recipe.name,
                "description": self.recipe.description,
            },
            "status": self.status,
            "created_at": self.created_at_iso,
            "prometheus_url": self.prometheus_url,
            "grafana_url": self.grafana_url,
            "targets": list(self.targets),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], recipe: MonitorRecipe) -> "MonitorInstance":
        return MonitorInstance(
            id=str(data.get("id")),
            recipe=recipe,
            status=MonitorStatus(data.get("status", MonitorStatus.STOPPED)),
            created_at_iso=str(data.get("created_at")),
            prometheus_url=data.get("prometheus_url"),
            grafana_url=data.get("grafana_url"),
            targets=list(data.get("targets") or []),
            metadata=dict(data.get("metadata") or {}),
        )
