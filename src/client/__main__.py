import sys
import json
import argparse
from pathlib import Path
from .manager import ClientManager


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
    
    add_parser = subparsers.add_parser('add', help='Add a client')
    add_parser.add_argument('--name', required=True, help='Client name')
    add_parser.add_argument('--recipe', required=True, help='Recipe name')
    add_parser.add_argument('--endpoint', help='Override endpoint')
    
    remove_parser = subparsers.add_parser('remove', help='Remove a client')
    remove_parser.add_argument('--name', required=True, help='Client name')
    
    stop_parser = subparsers.add_parser('stop-all', help='Stop all running clients')
    
    metrics_parser = subparsers.add_parser('metrics', help='Collect metrics')
    metrics_parser.add_argument('--output', default='./results/metrics.json', help='Output file')
    
    info_parser = subparsers.add_parser('info', help='Get recipe info')
    info_parser.add_argument('--recipe', required=True, help='Recipe name')
    
    template_parser = subparsers.add_parser('template', help='Create recipe template')
    template_parser.add_argument('--name', required=True, help='Template name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
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
    
    elif args.command == 'add':
        try:
            config = {
                'recipe': args.recipe,
                'endpoint': args.endpoint
            }
            client = manager.add_client(args.name, config)
            print(f"Client added: {args.name} (ID: {client.id})")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'remove':
        if manager.remove_client(args.name):
            print(f"Client removed: {args.name}")
        else:
            print(f"Client not found: {args.name}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'stop-all':
        stopped = manager.stop_all()
        print(f"Stopped {len(stopped)} client(s)")
        for name in stopped:
            print(f"  - {name}")
    
    elif args.command == 'metrics':
        metrics = manager.collect_metrics()
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"Metrics saved to: {output_path}")
        print(f"\nTotal clients: {len(metrics)}")
        
        for m in metrics:
            print(f"\nClient: {m['client_name']}")
            print(f"  Status: {m['status']}")
            print(f"  Recipe: {m['recipe_name']}")
            if 'total_requests' in m:
                print(f"  Requests: {m['total_requests']}")
                print(f"  Successes: {m['successes']}")
                print(f"  Errors: {m['errors']}")
    
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
    
    elif args.command == 'template':
        path = manager.recipe_loader.create_recipe_template(args.name)
        print(f"Template created: {path}")


if __name__ == '__main__':
    main()
