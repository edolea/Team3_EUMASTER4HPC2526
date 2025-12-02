"""Command line interface for monitor deployments."""

from __future__ import annotations

import argparse
import sys

from loguru import logger
from .manager import MonitorManager


def handle_monitor_commands(args) -> None:
    """Handle monitor commands from unified CLI"""
    
    if not args.command:
        print("Error: No command specified", file=sys.stderr)
        sys.exit(1)
    
    manager = MonitorManager()

    if args.command == "start":
        try:
            target_job_ids = None
            if hasattr(args, 'targets') and args.targets:
                target_job_ids = [t.strip() for t in args.targets.split(",")]

            instance = manager.start_monitor(
                recipe_name=args.recipe,
                target_job_ids=target_job_ids,
            )

            print(f"\n✓ Monitoring stack started!")
            print(f"   Monitor ID: {instance.id}")
            print(f"   Recipe: {instance.recipe.name}")
            print(f"   Status: {instance.status}\n")

            if instance.prometheus_url:
                print(f"   Prometheus: {instance.prometheus_url}")
                print(f"   Targets: {instance.prometheus_url}/targets\n")

            print(f"   Resolved targets:")
            for name, endpoint in instance.targets.items():
                print(f"     - {name}: {endpoint}")

        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            logger.exception("Failed to start monitor")
            sys.exit(1)

    elif args.command == "stop":
        if manager.stop_monitor(args.id):
            print(f"✓ Monitor stopped: {args.id}")
        else:
            print(f"✗ Failed to stop monitor: {args.id}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "list":
        print("\n📊 Available Monitor Recipes:")
        recipes = manager.list_available_recipes()
        if recipes:
            for recipe in recipes:
                info = manager.recipe_loader.get_recipe_info(recipe)
                if info:
                    print(f"   • {recipe}: {info.get('description', '')}")
        else:
            print("   No recipes found")

        print("\n🔍 Running Monitors:")
        monitors = manager.list_running_monitors()
        if monitors:
            for m in monitors:
                print(f"   • {m.id[:8]}... ({m.recipe.name})")
                print(f"     Status: {m.status}")
                if m.prometheus_url:
                    print(f"     Prometheus: {m.prometheus_url}")
        else:
            print("   No monitors running")

    elif args.command == "status":
        try:
            status = manager.get_monitor_status(args.id)
            print(f"\n📊 Monitor Status: {status['id'][:8]}...")
            print(f"   Recipe: {status['recipe']['name']}")
            print(f"   Status: {status['status']}")
            print(f"   Created: {status['created_at']}")
            
            if status.get('prometheus_url'):
                print(f"\n   Prometheus: {status['prometheus_url']}")
            
            print(f"\n   Targets:")
            for name, endpoint in status.get('targets', {}).items():
                print(f"     - {name}: {endpoint}")
            
            print(f"\n   Components:")
            for name, comp in status.get('components', {}).items():
                print(f"     - {name}: {comp['endpoint']} (Job: {comp['job_id']}, Status: {comp['status']})")

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "stop-all":
        monitors = manager.list_running_monitors()
        stopped = 0
        for m in monitors:
            if manager.stop_monitor(m.id):
                stopped += 1
                print(f"✓ Stopped: {m.id[:8]}...")
        print(f"\nStopped {stopped} monitor(s)")

    elif args.command == "info":
        info = manager.recipe_loader.get_recipe_info(args.recipe)
        if not info:
            print(f"Recipe not found: {args.recipe}", file=sys.stderr)
            sys.exit(1)

        print(f"\nRecipe: {info['name']}")
        print(f"Description: {info['description']}")
        print(f"Targets: {', '.join(info['targets'])}")
        print(f"Prometheus: {'enabled' if info['prometheus_enabled'] else 'disabled'}")
        if info.get('file_path'):
            print(f"Location: {info['file_path']}")

    elif args.command == "export":
        try:
            # Parse custom queries if provided
            custom_queries = None
            if hasattr(args, 'queries') and args.queries:
                custom_queries = {}
                for query_str in args.queries.split(','):
                    if ':' in query_str:
                        name, desc = query_str.split(':', 1)
                        custom_queries[name.strip()] = desc.strip()
                    else:
                        custom_queries[query_str.strip()] = "Custom query"

            output_file = manager.export_prometheus_metrics(
                monitor_id=args.id,
                output_dir=args.output if hasattr(args, 'output') and args.output else None,
                format=args.format if hasattr(args, 'format') else 'json',
                export_type=args.type if hasattr(args, 'type') else 'instant',
                custom_queries=custom_queries,
                start=args.start if hasattr(args, 'start') and args.start else None,
                end=args.end if hasattr(args, 'end') and args.end else None,
                step=args.step if hasattr(args, 'step') else '15s',
            )

            if output_file:
                print(f"\n✓ Metrics exported successfully!")
                print(f"   File: {output_file}")
            else:
                print(f"✗ Failed to export metrics", file=sys.stderr)
                sys.exit(1)

        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            logger.exception("Failed to export metrics")
            sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build standalone CLI parser for monitor module"""
    parser = argparse.ArgumentParser(
        description="Monitor deployment CLI",
        prog="python -m monitor",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start monitor
    start_parser = subparsers.add_parser("start", help="Start a monitoring stack from a recipe")
    start_parser.add_argument("--recipe", required=True, help="Recipe name to deploy")
    start_parser.add_argument(
        "--targets",
        help="Comma-separated SLURM job IDs to monitor (optional)",
    )

    # Stop monitor
    stop_parser = subparsers.add_parser("stop", help="Stop a running monitor instance")
    stop_parser.add_argument("--id", required=True, help="Monitor ID to stop")

    # List
    subparsers.add_parser("list", help="List available recipes and running monitors")

    # Status
    status_parser = subparsers.add_parser("status", help="Get status of a monitor")
    status_parser.add_argument("--id", required=True, help="Monitor ID")

    # Stop all
    subparsers.add_parser("stop-all", help="Stop all running monitors")

    # Recipe info
    info_parser = subparsers.add_parser("info", help="Show information about a recipe")
    info_parser.add_argument("--recipe", required=True, help="Recipe name")

    # Export metrics
    export_parser = subparsers.add_parser("export", help="Export Prometheus metrics to JSON/CSV")
    export_parser.add_argument("--id", required=True, help="Monitor ID")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    export_parser.add_argument("--type", choices=["instant", "range", "all"], default="instant",
                              help="Export type: instant (current values), range (time-series), all (all metrics)")
    export_parser.add_argument("--output", help="Output directory (default: logs/monitors/<id>/metrics/)")
    export_parser.add_argument("--queries", help="Comma-separated custom queries (format: metric:description)")
    export_parser.add_argument("--start", help="Start time for range queries (RFC3339 or Unix timestamp)")
    export_parser.add_argument("--end", help="End time for range queries (RFC3339 or Unix timestamp)")
    export_parser.add_argument("--step", default="15s", help="Step size for range queries (default: 15s)")

    return parser


def main() -> None:
    """Standalone entry point for monitor module"""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    handle_monitor_commands(args)


if __name__ == "__main__":
    main()
