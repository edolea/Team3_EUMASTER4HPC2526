from pathlib import Path
import yaml
from .recipe import ClientRecipe


class RecipeLoader:
    def __init__(self, recipe_directory='recipes/clients'):
        self.recipe_directory = Path(recipe_directory)
        self._cache = {}
        self.recipe_directory.mkdir(parents=True, exist_ok=True)

    def load_recipe(self, name):
        if name in self._cache:
            return self._cache[name]
        
        recipe_path = self._find_recipe_file(name)
        if not recipe_path:
            raise FileNotFoundError(f"Recipe not found: {name}")
        
        recipe = ClientRecipe.from_yaml(str(recipe_path))
        errors = self.validate_recipe(recipe)
        if errors:
            raise ValueError(f"Recipe validation failed: {', '.join(errors)}")
        
        self._cache[name] = recipe
        return recipe

    def list_available_recipes(self):
        recipes = []
        for pattern in ['*.yml', '*.yaml']:
            for recipe_file in self.recipe_directory.glob(pattern):
                recipes.append(recipe_file.stem)
        return sorted(recipes)

    def validate_recipe(self, recipe):
        errors = []
        try:
            recipe.validate()
        except ValueError as e:
            errors.append(str(e))
        
        MAX_CONCURRENT_USERS = 1000
        MAX_DURATION_SECONDS = 5000
        if recipe.workload.get('concurrent_users', 0) > MAX_CONCURRENT_USERS:
            errors.append(f"Concurrent users exceeds reasonable limit ({MAX_CONCURRENT_USERS})")

        if recipe.workload.get('duration_seconds', 0) > MAX_DURATION_SECONDS:
            errors.append(f"Duration exceeds reasonable limit ({MAX_DURATION_SECONDS} seconds)")

        return errors

    def get_recipe_info(self, name):
        recipe_path = self._find_recipe_file(name)
        if not recipe_path:
            return {}
        
        try:
            with open(recipe_path, 'r') as f:
                data = yaml.safe_load(f)
            
            return {
                'name': data.get('name', name),
                'description': data.get('description', 'No description'),
                'file_path': str(recipe_path),
                'target_service': data.get('target', {}).get('service', 'unknown'),
                'workload_pattern': data.get('workload', {}).get('pattern', 'unknown'),
            }
        except Exception:
            return {}


    def _find_recipe_file(self, name):
        for ext in ['.yml', '.yaml']:
            recipe_path = self.recipe_directory / f"{name}{ext}"
            if recipe_path.exists():
                return recipe_path
        return None
