"""High-level orchestration for server deployments."""

from __future__ import annotations

from typing import Dict, List

from .recipe_loader import ServerRecipeLoader
from .server_instance import ServerInstance
from .orchestrator import ServerOrchestrator


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
                status = self.orchestrator.status(instance.orchestrator_handle)
                instance.update_status(status)
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
