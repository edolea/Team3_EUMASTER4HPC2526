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
    PENDING = "PENDING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    FAILED = "FAILED"

@dataclass
class TargetService:
    """Target service to monitor"""
    name: str
    job_id: Optional[str] = None
    endpoint: Optional[str] = None
    metrics_path: str = "/metrics"
    port: int = 8000

    def validate(self) -> bool:
        if not self.name and not self.endpoint:
            raise ValueError("Either name or endpoint must be specified")
        return True

@dataclass
class PrometheusConfig:
    """Prometheus component configuration"""
    enabled: bool = True
    image: str = "docker://prom/prometheus:latest"
    scrape_interval: str = "15s"
    retention_time: str = "24h"
    port: int = 9090
    partition: str = "cpu"
    resources: Dict[str, Any] = field(
        default_factory=lambda: {
            "cpu_cores": 2,
            "memory_gb": 4,
            "gpu_count": 0,
        }
    )

    def validate(self) -> bool:
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")
        return True

@dataclass
class MonitorRecipe:
    name: str
    description: str
    targets: List[TargetService]
    prometheus: PrometheusConfig
    service_name: str = ""

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
        
        # Parse targets
        targets = []
        for t in data.get("targets", []):
            if isinstance(t, str):
                # Legacy format: simple string
                targets.append(TargetService(name=name, endpoint=t))
            else:
                # New format: dict with name, port, etc.
                targets.append(
                    TargetService(
                        name=t.get("name", ""),
                        job_id=t.get("job_id"),
                        endpoint=t.get("endpoint"),
                        metrics_path=t.get("metrics_path", "/metrics"),
                        port=t.get("port", 8000),
                    )
                )
        
        # Parse Prometheus config
        prom_data = data.get("prometheus", {})
        prometheus = PrometheusConfig(
            enabled=prom_data.get("enabled", True),
            image=prom_data.get("image", "docker://prom/prometheus:latest"),
            scrape_interval=prom_data.get("scrape_interval", "15s"),
            retention_time=prom_data.get("retention_time", "24h"),
            port=prom_data.get("port", 9090),
            partition=prom_data.get("partition", "cpu"),
            resources=prom_data.get("resources", {}),
        )
        
        recipe = MonitorRecipe(
            name=name,
            description=description,
            targets=targets,
            prometheus=prometheus,
            service_name=data.get("service_name", name),
        )
        recipe.validate()
        return recipe

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Recipe.name must not be empty")
        if not self.targets:
            raise ValueError("At least one target is required")
        for target in self.targets:
            target.validate()
        self.prometheus.validate()

    def to_prometheus_config(self, resolved_targets: Dict[str, str]) -> Dict[str, Any]:
        """Generate Prometheus configuration
        
        Args:
            resolved_targets: Dict of {target_name: "host:port"}
        """
        scrape_configs = []
        
        for target_name, endpoint in resolved_targets.items():
            # Find corresponding target spec
            target_spec = next((t for t in self.targets if t.name == target_name), None)
            metrics_path = target_spec.metrics_path if target_spec else "/metrics"
            
            scrape_configs.append({
                "job_name": target_name,
                "static_configs": [{"targets": [endpoint]}],
                "metrics_path": metrics_path,
                "scrape_interval": self.prometheus.scrape_interval,
            })
        
        return {
            "global": {
                "scrape_interval": self.prometheus.scrape_interval,
                "evaluation_interval": self.prometheus.scrape_interval,
            },
            "scrape_configs": scrape_configs,
        }


@dataclass
class MonitorComponent:
    """Individual component of the monitoring stack"""
    name: str
    job_id: str
    endpoint: str
    status: MonitorStatus = MonitorStatus.PENDING

@dataclass
class MonitorInstance:
    id: str
    recipe: MonitorRecipe
    status: MonitorStatus
    created_at_iso: str
    prometheus_url: Optional[str] = None
    targets: Dict[str, str] = field(default_factory=dict)  # {target_name: "host:port"}
    components: Dict[str, MonitorComponent] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_component(self, name: str, job_id: str, endpoint: str) -> None:
        """Add a component to the monitoring stack"""
        component = MonitorComponent(
            name=name,
            job_id=job_id,
            endpoint=endpoint,
        )
        self.components[name] = component
        if name == "prometheus":
            self.prometheus_url = endpoint

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
            "targets": dict(self.targets),
            "components": {
                name: {
                    "job_id": comp.job_id,
                    "endpoint": comp.endpoint,
                    "status": comp.status,
                }
                for name, comp in self.components.items()
            },
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], recipe: MonitorRecipe) -> "MonitorInstance":
        instance = MonitorInstance(
            id=str(data.get("id")),
            recipe=recipe,
            status=MonitorStatus(data.get("status", MonitorStatus.STOPPED)),
            created_at_iso=str(data.get("created_at")),
            prometheus_url=data.get("prometheus_url"),
            targets=dict(data.get("targets") or {}),
            metadata=dict(data.get("metadata") or {}),
        )
        
        # Restore components
        for name, comp_data in data.get("components", {}).items():
            instance.components[name] = MonitorComponent(
                name=name,
                job_id=comp_data.get("job_id", ""),
                endpoint=comp_data.get("endpoint", ""),
                status=MonitorStatus(comp_data.get("status", MonitorStatus.STOPPED)),
            )
        
        return instance
