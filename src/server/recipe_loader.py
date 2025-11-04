"""Utilities for discovering and validating server recipes."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .recipe import ServerRecipe


class ServerRecipeLoader:
    """Loads server recipes from a directory on disk."""

    def __init__(self, recipe_directory: str = "recipes/servers") -> None:
        self.recipe_directory = Path(recipe_directory)
        self.recipe_directory.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, ServerRecipe] = {}

    # ------------------------------------------------------------------
    def load_recipe(self, name: str) -> ServerRecipe:
        if name in self._cache:
            return self._cache[name]

        recipe_path = self._find_recipe_file(name)
        if not recipe_path:
            raise FileNotFoundError(f"Recipe not found: {name}")

        recipe = ServerRecipe.from_yaml(str(recipe_path))
        self._cache[name] = recipe
        return recipe

    # ------------------------------------------------------------------
    def list_available_recipes(self) -> List[str]:
        recipes: List[str] = []
        for pattern in ("*.yml", "*.yaml"):
            recipes.extend(sorted(f.stem for f in self.recipe_directory.glob(pattern)))
        return sorted(set(recipes))

    # ------------------------------------------------------------------
    def get_recipe_info(self, name: str) -> Dict[str, str]:
        recipe_path = self._find_recipe_file(name)
        if not recipe_path:
            return {}

        with open(recipe_path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        return {
            "name": data.get("name", name),
            "description": data.get("description", "No description"),
            "file_path": str(recipe_path),
            "command": data.get("service", {}).get("command", "unknown"),
        }

    # ------------------------------------------------------------------
    def create_recipe_template(self, name: str) -> Path:
        """Create a new recipe file populated with a starter template."""

        destination = self.recipe_directory / f"{name}.yaml"
        if destination.exists():
            raise FileExistsError(f"Recipe already exists: {destination}")

        template = {
            "name": name,
            "description": "Describe the service this recipe deploys.",
            "service": {
                "command": "python -m http.server 8000",
                "working_dir": "./",
                "env": {
                    "EXAMPLE_ENV": "value",
                },
                "ports": [8000],
            },
            "orchestration": {
                "resources": {
                    "cpu_cores": 2,
                    "memory_gb": 4,
                }
            },
        }

        with open(destination, "w", encoding="utf-8") as handle:
            yaml.safe_dump(template, handle, sort_keys=False)

        return destination

    # ------------------------------------------------------------------
    def _find_recipe_file(self, name: str) -> Optional[Path]:
        for ext in (".yml", ".yaml"):
            candidate = self.recipe_directory / f"{name}{ext}"
            if candidate.exists():
                return candidate
        return None


__all__ = ["ServerRecipeLoader"]
