"""High-level orchestration for server deployments."""

from __future__ import annotations

from typing import Dict, List

from .recipe_loader import ServerRecipeLoader
from .server_instance import ServerInstance, ServerStatus
from .orchestrator import ServerOrchestrator
from src.discover import write_discover_info, clear_discover_info


class ServerManager:
    """Coordinates recipe management and SLURM submissions for servers."""

    def __init__(self, recipe_directory: str = "recipes/servers") -> None:
        self.recipe_loader = ServerRecipeLoader(recipe_directory=recipe_directory)
        self.instances: Dict[str, ServerInstance] = {}
        self._orchestrator: ServerOrchestrator | None = None

    # ------------------------------------------------------------------
    @property
    def orchestrator(self) -> ServerOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = ServerOrchestrator()
        return self._orchestrator

    # ------------------------------------------------------------------
    def run(self, recipe_name: str, *, count: int = 1) -> List[ServerInstance]:
        recipe = self.recipe_loader.load_recipe(recipe_name)

        deployments: List[ServerInstance] = []
        for index in range(count):
            instance = ServerInstance(
                recipe_name=recipe.name,
                orchestrator_handle=f"pending-{index}",
                command=recipe.service.get("command", ""),
                ports=recipe.ports,
            )

            try:
                job_id = self.orchestrator.submit(instance, recipe)
            except Exception as exc:
                instance.mark_failed()
                raise RuntimeError(f"Failed to submit server job: {exc}") from exc

            instance.orchestrator_handle = job_id
            instance.mark_starting()

            # Write discovery information
            discover_data = {
                "job_id": job_id,
                "recipe_name": recipe.name,
                "instance_id": instance.id,
            }
            write_discover_info(recipe.name, discover_data)

            name = f"{recipe.name}-{instance.id[:8]}"
            self.instances[name] = instance
            deployments.append(instance)

        return deployments

    # ------------------------------------------------------------------
    def stop(self, name: str) -> bool:
        instance = self.instances.get(name)
        if not instance:
            return False

        if self.orchestrator.stop(instance.orchestrator_handle):
            instance.cancel()
            clear_discover_info(instance.recipe_name)  # Clear discovery info
            return True

        return False

    # ------------------------------------------------------------------
    def stop_all(self) -> List[str]:
        stopped: List[str] = []
        for name in list(self.instances.keys()):
            if self.stop(name):
                stopped.append(name)
        return stopped

    # ------------------------------------------------------------------
    def collect_status(self) -> List[Dict[str, str]]:
        status_list: List[Dict[str, str]] = []
        for name, instance in self.instances.items():
            try:
                status_info = self.orchestrator.status(instance.orchestrator_handle)
                instance.update_status(status_info)

                # Update discovery info if running
                if instance.status == ServerStatus.RUNNING:
                    discover_data = {
                        "job_id": instance.orchestrator_handle,
                        "recipe_name": instance.recipe_name,
                        "instance_id": instance.id,
                        "node": instance.metadata.get("node"),
                        "ports": instance.ports,
                    }
                    write_discover_info(instance.recipe_name, discover_data)

            except Exception:
                # Failure to query SLURM should not break status collection.
                pass

            status_list.append({
                "name": name,
                **instance.get_metrics(),
            })

        return status_list

    # ------------------------------------------------------------------
    def list_available_recipes(self) -> List[str]:
        return self.recipe_loader.list_available_recipes()

    # ------------------------------------------------------------------
    def info(self, recipe_name: str) -> Dict[str, str]:
        return self.recipe_loader.get_recipe_info(recipe_name)


__all__ = ["ServerManager"]
