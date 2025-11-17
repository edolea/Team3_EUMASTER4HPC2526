from __future__ import annotations

import json
import time
import uuid
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .models import MonitorInstance, MonitorRecipe, MonitorStatus
from .recipe_loader import MonitorRecipeLoader
from .orchestrator import MonitorOrchestrator


class MonitorManager:
    """
    Central orchestration for monitoring stacks
    Manages lifecycle of Prometheus monitoring for AI services
    """

    def __init__(
        self,
        recipe_loader: Optional[MonitorRecipeLoader] = None,
        recipe_directory: str = "recipes/monitors",
        output_root: str = "logs/monitors",
    ) -> None:
        self.recipe_loader = recipe_loader or MonitorRecipeLoader(
            recipe_directory=recipe_directory
        )
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        self.orchestrator = MonitorOrchestrator(log_directory=str(self.output_root / "slurm"))
        
        self._instances: Dict[str, MonitorInstance] = {}
        self._state_file = self.output_root / "instances.json"
        self._load_state()

        logger.info("MonitorManager initialization complete")

    # ---------- lifecycle ----------
    def list_available_recipes(self) -> List[str]:
        """List available monitor recipes"""
        return self.recipe_loader.list_available()

    def list_running_monitors(self) -> List[MonitorInstance]:
        """List running monitor instances"""
        return [m for m in self._instances.values() if m.status == MonitorStatus.RUNNING]

    def start_monitor(
        self,
        recipe_name: str,
        target_job_ids: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> MonitorInstance:
        """
        Start a monitoring stack from a recipe

        Args:
            recipe_name: Name of the monitor recipe
            target_job_ids: Optional list of SLURM job IDs to monitor
            metadata: Optional metadata dict

        Returns:
            MonitorInstance for the started monitoring stack
        """
        logger.info(f"Starting monitor from recipe: {recipe_name}")

        # Load recipe
        recipe = self.recipe_loader.load_recipe(recipe_name)
        
        # Create instance
        monitor_id = str(uuid.uuid4())
        created_at_iso = datetime.utcnow().isoformat() + "Z"
        instance = MonitorInstance(
            id=monitor_id,
            recipe=recipe,
            status=MonitorStatus.STARTING,
            created_at_iso=created_at_iso,
            metadata=metadata or {},
        )
        self._instances[monitor_id] = instance
        self._save_state()

        # Resolve target endpoints
        targets = self._resolve_targets(recipe.targets, target_job_ids)
        
        if not targets:
            instance.status = MonitorStatus.ERROR
            self._save_state()
            raise RuntimeError("No valid targets found to monitor")

        instance.targets = targets
        logger.info(f"Resolved targets: {targets}")

        # Setup directories
        instance_dir = self.output_root / instance.id
        prom_config_dir = instance_dir / "prometheus" / "config"
        prom_data_dir = instance_dir / "prometheus" / "data"

        for dir_path in [prom_config_dir, prom_data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Deploy Prometheus
        if recipe.prometheus.enabled:
            logger.info("Deploying Prometheus...")
            prom_job_id = self.orchestrator.deploy_prometheus(
                config=recipe.prometheus,
                targets=targets,
                config_dir=prom_config_dir,
                data_dir=prom_data_dir,
            )

            # Wait for Prometheus to be running and get its node
            logger.info("Waiting for Prometheus to be running...")
            prom_node = self._wait_for_job_node(prom_job_id, timeout_seconds=120)

            if not prom_node:
                logger.error("Prometheus failed to start or timeout reached")
                instance.status = MonitorStatus.ERROR
                self._save_state()
                # Clean up the failed job
                try:
                    self.orchestrator.stop_component(prom_job_id)
                except Exception as e:
                    logger.warning(f"Failed to stop Prometheus job: {e}")
                raise RuntimeError("Prometheus failed to start or timeout reached")

            prom_url = f"http://{prom_node}:{recipe.prometheus.port}"
            instance.add_component("prometheus", prom_job_id, prom_url)
            logger.info(f"Prometheus deployed and running: {prom_url}")

        # Update status
        instance.status = MonitorStatus.RUNNING
        self._save_state()

        logger.info(f"Monitor started successfully: {instance.id}")
        return instance

    def stop_monitor(self, monitor_id: str) -> bool:
        """Stop a running monitor"""
        logger.info(f"Stopping monitor: {monitor_id}")

        inst = self._instances.get(monitor_id)
        if not inst:
            logger.warning(f"Monitor not found: {monitor_id}")
            return False

        if inst.status in (MonitorStatus.STOPPING, MonitorStatus.STOPPED):
            return True

        inst.status = MonitorStatus.STOPPING
        self._save_state()

        # Stop all components
        success = True
        for name, component in inst.components.items():
            logger.info(f"Stopping component: {name} ({component.job_id})")
            if not self.orchestrator.stop_component(component.job_id):
                logger.error(f"Failed to stop component: {name}")
                success = False

        if success:
            inst.status = MonitorStatus.STOPPED
            logger.info(f"Monitor stopped successfully: {monitor_id}")
        else:
            inst.status = MonitorStatus.ERROR
            logger.error(f"Failed to stop all components for monitor: {monitor_id}")

        self._save_state()
        return success

    def get_monitor_status(self, monitor_id: str) -> Dict:
        """Get status of a monitor"""
        logger.info(f"Getting status for monitor: {monitor_id}")

        instance = self._instances.get(monitor_id)
        if not instance:
            raise ValueError(f"Monitor not found: {monitor_id}")

        # Update component statuses
        for name, component in instance.components.items():
            status = self.orchestrator.get_component_status(component.job_id)
            component.status = status

        return instance.to_dict()

    def export_metrics(self, monitor_id: str, output_path: str) -> Optional[Path]:
        """Export monitor metrics snapshot"""
        inst = self._instances.get(monitor_id)
        if not inst:
            logger.warning(f"Monitor not found: {monitor_id}")
            return None
        
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
        """Stop all running instances"""
        for inst in list(self._instances.values()):
            if inst.status == MonitorStatus.RUNNING:
                self.stop_monitor(inst.id)

    def _resolve_targets(
        self,
        target_specs: List,
        job_ids: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Resolve target services to endpoints
        
        Args:
            target_specs: List of TargetService objects
            job_ids: Optional list of SLURM job IDs
        
        Returns:
            Dict of {target_name: "host:port"}
        """
        targets = {}

        for i, spec in enumerate(target_specs):
            # If job_id provided, use it
            if job_ids and i < len(job_ids):
                job_id = job_ids[i]
                # Wait for the target job to be running
                node = self._wait_for_job_node(job_id, timeout_seconds=60)
                if node:
                    targets[spec.name] = f"{node}:{spec.port}"
                    logger.info(f"Resolved {spec.name} -> {node}:{spec.port}")
                else:
                    logger.warning(f"Could not resolve node for job {job_id}")
            # If endpoint directly specified
            elif spec.endpoint:
                targets[spec.name] = spec.endpoint
                logger.info(f"Using direct endpoint for {spec.name}: {spec.endpoint}")
            # Try to find by service name in spec's job_id
            elif spec.job_id:
                node = self._wait_for_job_node(spec.job_id, timeout_seconds=60)
                if node:
                    targets[spec.name] = f"{node}:{spec.port}"
                    logger.info(f"Resolved {spec.name} -> {node}:{spec.port}")

        return targets

    def _wait_for_job_node(
        self, job_id: str, timeout_seconds: int = 120
    ) -> Optional[str]:
        """
        Wait for a SLURM job to be running and return its node

        Args:
            job_id: SLURM job ID
            timeout_seconds: Maximum time to wait

        Returns:
            Node hostname if job is running, None if timeout or job failed
        """
        start_time = time.time()
        last_status = None

        logger.info(
            f"Waiting for job {job_id} to be running (timeout: {timeout_seconds}s)..."
        )

        while (time.time() - start_time) < timeout_seconds:
            try:
                result = subprocess.run(
                    ["squeue", "-j", job_id, "--format=%T|%N", "--noheader"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                output = result.stdout.strip()
                if not output:
                    logger.warning(f"Job {job_id} not found in queue")
                    return None

                parts = output.split("|")
                if len(parts) >= 2:
                    status, node = parts[0].strip(), parts[1].strip()

                    # Log status changes
                    if status != last_status:
                        logger.info(f"Job {job_id} status: {status}")
                        last_status = status

                    if status == "RUNNING" and node:
                        elapsed = time.time() - start_time
                        logger.info(
                            f"✓ Job {job_id} is running on node {node} (took {elapsed:.1f}s)"
                        )
                        return node
                    elif status == "PENDING":
                        logger.debug(f"Job {job_id} is pending, waiting...")
                    elif status in ["FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL"]:
                        logger.error(f"✗ Job {job_id} failed with status {status}")
                        return None

            except subprocess.CalledProcessError as e:
                logger.warning(f"Error checking job {job_id}: {e}")

            time.sleep(5)

        elapsed = time.time() - start_time
        logger.error(
            f"✗ Timeout waiting for job {job_id} to start (waited {elapsed:.1f}s)"
        )
        return None

    # ---------- persistence ----------
    def _save_state(self) -> None:
        data = []
        for inst in self._instances.values():
            d = inst.to_dict()
            d["recipe_file"] = inst.recipe.name
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
        except Exception as exc:
            logger.warning(f"Failed to load state: {exc}")
