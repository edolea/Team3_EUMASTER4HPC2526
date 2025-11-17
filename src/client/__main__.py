import sys
import json
import argparse
from pathlib import Path
from .manager import ClientManager


def handle_client_commands(args):
    """Handle client commands from unified CLI"""
    
    if not args.command:
        print("Error: No command specified", file=sys.stderr)
        sys.exit(1)
    
    manager = ClientManager()
    
    if args.command == 'run':
        try:
            results = manager.run_bench(args.recipe, runs=args.runs)
            print(f"Started {len(results)} benchmark run(s)")
            for r in results:
                print(f"  - Run ID: {r.id}, Status: {r.status.value}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'list':
        recipes = manager.list_available_clients()
        print("Available recipes:")
        for recipe in recipes:
            print(f"  - {recipe}")
    
    elif args.command == 'info':
        info = manager.recipe_loader.get_recipe_info(args.recipe)
        if info:
            print(f"Recipe: {info['name']}")
            print(f"Description: {info['description']}")
            print(f"Target: {info['target_service']}")
            print(f"Pattern: {info['workload_pattern']}")
            print(f"Path: {info['file_path']}")
        else:
            print(f"Recipe not found: {args.recipe}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark Client CLI',
        prog='python -m client'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    run_parser = subparsers.add_parser('run', help='Run a benchmark')
    run_parser.add_argument('--recipe', required=True, help='Recipe name')
    run_parser.add_argument('--runs', type=int, default=1, help='Number of runs')
    run_parser.add_argument('--output', default='./results', help='Output directory')
    
    list_parser = subparsers.add_parser('list', help='List available recipes')
    
    info_parser = subparsers.add_parser('info', help='Get recipe info')
    info_parser.add_argument('--recipe', required=True, help='Recipe name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    handle_client_commands(args)


if __name__ == '__main__':
    main()
