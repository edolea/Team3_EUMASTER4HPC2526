from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .models import MonitorInstance, MonitorRecipe, MonitorStatus
from .recipe_loader import MonitorRecipeLoader
from .prometheus_client import PrometheusClient

class MonitorManager:
    def __init__(
        self,
        recipe_loader: MonitorRecipeLoader,
        output_root: str = "monitor_output",
    ) -> None:
        self.recipe_loader = recipe_loader
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._instances: Dict[str, MonitorInstance] = {}
        self._state_file = self.output_root / "instances.json"
        self._prom = PrometheusClient(workdir=str(self.output_root / ".prometheus"))
        self._load_state()

    # ---------- lifecycle ----------
    def list_available_recipes(self) -> List[str]:
        return self.recipe_loader.list_available()

    def list_running_monitors(self) -> List[MonitorInstance]:
        return [m for m in self._instances.values() if m.status == MonitorStatus.RUNNING]

    def start_monitor(
        self,
        recipe_name: str,
        targets: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        mode: str = "local",
        prometheus_bin: Optional[str] = None,
        port: int = 9090,
    ) -> MonitorInstance:
        recipe = self.recipe_loader.load_recipe(recipe_name)
        monitor_id = str(uuid.uuid4())
        created_at_iso = datetime.utcnow().isoformat() + "Z"
        instance = MonitorInstance(
            id=monitor_id,
            recipe=recipe,
            status=MonitorStatus.STARTING,
            created_at_iso=created_at_iso,
            targets=targets or recipe.target_services,
            metadata=metadata or {},
        )
        self._instances[monitor_id] = instance
        self._save_state()

        # Deploy Prometheus (stub if no binary provided)
        config = recipe.to_prometheus_config(targets=instance.targets)
        url = self._prom.deploy(instance.targets, config, prometheus_bin=prometheus_bin, port=port)
        instance.prometheus_url = url
        instance.status = MonitorStatus.RUNNING
        self._save_state()

        logger.info(f"Monitor started: {instance.id} ({recipe.name}) -> {url}")
        return instance

    def stop_monitor(self, monitor_id: str) -> bool:
        inst = self._instances.get(monitor_id)
        if not inst:
            logger.warning(f"Monitor not found: {monitor_id}")
            return False
        if inst.status in (MonitorStatus.STOPPING, MonitorStatus.STOPPED):
            return True
        inst.status = MonitorStatus.STOPPING
        self._save_state()

        # Stop Prometheus (if we own it)
        self._prom.stop()

        inst.status = MonitorStatus.STOPPED
        self._save_state()
        logger.info(f"Monitor stopped: {monitor_id}")
        return True

    def export_metrics(self, monitor_id: str, output_path: str) -> Optional[Path]:
        inst = self._instances.get(monitor_id)
        if not inst:
            logger.warning(f"Monitor not found: {monitor_id}")
            return None
        # For the demo we just export the instance state and targets as JSON
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "monitor": inst.to_dict(),
            "exported_at": datetime.utcnow().isoformat() + "Z",
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info(f"Exported monitor snapshot to {out}")
        return out

    def shutdown(self) -> None:
        # stop all running instances
        for inst in list(self._instances.values()):
            if inst.status == MonitorStatus.RUNNING:
                self.stop_monitor(inst.id)

    # ---------- persistence ----------
    def _save_state(self) -> None:
        data = []
        for inst in self._instances.values():
            d = inst.to_dict()
            d["recipe_file"] = inst.recipe.name  # reference by name
            data.append(d)
        self._state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            raw = json.loads(self._state_file.read_text(encoding="utf-8"))
            for d in raw:
                name = d.get("recipe", {}).get("name")
                if not name:
                    continue
                try:
                    rec = self.recipe_loader.load_recipe(name)
                except Exception:
                    continue
                inst = MonitorInstance.from_dict(d, recipe=rec)
                self._instances[inst.id] = inst
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Failed to load state: {exc}")
