from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .models import MonitorRecipe

class MonitorRecipeLoader:
    def __init__(self, recipe_directory: str = "recipes") -> None:
        self.recipe_directory = Path(recipe_directory)
        self._cache: Dict[str, MonitorRecipe] = {}

    def _find_recipe_file(self, name: str) -> Optional[Path]:
        # look for name.yml or name.yaml in recipe_directory
        for ext in (".yml", ".yaml"):
            p = self.recipe_directory / f"{name}{ext}"
            if p.exists():
                return p
        # Also allow exact path
        p = Path(name)
        if p.exists():
            return p
        return None

    def list_available(self) -> List[str]:
        if not self.recipe_directory.exists():
            return []
        names: List[str] = []
        for p in self.recipe_directory.iterdir():
            if p.suffix in {".yml", ".yaml"}:
                names.append(p.stem)
        return sorted(names)

    def load_recipe(self, name: str) -> MonitorRecipe:
        if name in self._cache:
            return self._cache[name]
        path = self._find_recipe_file(name)
        if not path:
            raise FileNotFoundError(f"Monitor recipe not found: {name}")
        recipe = MonitorRecipe.from_yaml(str(path))
        recipe.validate()
        self._cache[name] = recipe
        logger.info(f"Loaded monitor recipe: {name}")
        return recipe
