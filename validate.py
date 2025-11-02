#!/usr/bin/env python3
"""
Quick validation script to check if the client module is properly set up
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    print("Testing imports...")
    try:
        from src.client.manager import ClientManager
        print("✓ ClientManager imported")
        
        from src.client.recipe import ClientRecipe
        print("✓ ClientRecipe imported")
        
        from src.client.recipe_loader import RecipeLoader
        print("✓ RecipeLoader imported")
        
        from src.client.client_instance import ClientInstance
        print("✓ ClientInstance imported")
        
        from src.client.orchestrator import ClientOrchestrator
        print("✓ ClientOrchestrator imported (note: needs SLURM_ACCOUNT)")
        
        from src.client.workload_runner import WorkloadRunner
        print("✓ WorkloadRunner imported")
        
        print("\n✓ All imports successful!")
        return True
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_recipe_loader():
    print("\n\nTesting RecipeLoader...")
    try:
        from src.client.recipe_loader import RecipeLoader
        
        loader = RecipeLoader('recipes/clients')
        print("✓ RecipeLoader created")
        
        recipes = loader.list_available_recipes()
        print(f"✓ Found {len(recipes)} recipes: {recipes}")
        
        if recipes:
            recipe = loader.load_recipe(recipes[0])
            print(f"✓ Loaded recipe: {recipe.name}")
            print(f"  - Target: {recipe.target.get('endpoint', 'N/A')}")
            print(f"  - Pattern: {recipe.workload.get('pattern', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"\n✗ RecipeLoader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manager():
    print("\n\nTesting ClientManager...")
    try:
        from src.client.manager import ClientManager
        
        manager = ClientManager('recipes/clients')
        print("✓ ClientManager created")
        
        recipes = manager.list_available_clients()
        print(f"✓ List recipes: {recipes}")
        
        return True
    except Exception as e:
        print(f"\n✗ ClientManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Client Module Validation")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_recipe_loader()
    all_passed &= test_manager()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        sys.exit(1)
