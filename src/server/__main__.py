"""Command line interface for server deployments."""

from __future__ import annotations

import argparse
import sys

from .manager import ServerManager


def handle_server_commands(args) -> None:
    """Handle server commands from unified CLI"""
    
    if not args.command:
        print("Error: No command specified", file=sys.stderr)
        sys.exit(1)
    
    manager = ServerManager()

    if args.command == "run":
        try:
            deployments = manager.run(args.recipe, count=args.count)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"Submitted {len(deployments)} instance(s)")
        for instance in deployments:
            print(f"  - {instance.recipe_name}:{instance.id[:8]} -> {instance.orchestrator_handle}")

    elif args.command == "list":
        recipes = manager.list_available_recipes()
        if not recipes:
            print("No recipes found")
        else:
            print("Available recipes:")
            for name in recipes:
                print(f"  - {name}")

    elif args.command == "stop":
        if manager.stop(args.name):
            print(f"Stopped instance: {args.name}")
        else:
            print(f"Instance not found or could not be stopped: {args.name}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "stop-all":
        stopped = manager.stop_all()
        print(f"Stopped {len(stopped)} instance(s)")
        for name in stopped:
            print(f"  - {name}")

    elif args.command == "status":
        statuses = manager.collect_status()
        if not statuses:
            print("No tracked instances")
        else:
            print("Tracked instances:")
            for info in statuses:
                print(f"  - {info['name']}")
                print(f"      Status: {info['status']}")
                print(f"      Uptime: {info['uptime_seconds']:.1f}s")
                if info.get("ports"):
                    print(f"      Ports:  {', '.join(str(p) for p in info['ports'])}")

    elif args.command == "info":
        info = manager.info(args.recipe)
        if not info:
            print(f"Recipe not found: {args.recipe}", file=sys.stderr)
            sys.exit(1)

        print(f"Recipe:       {info['name']}")
        print(f"Description:  {info['description']}")
        print(f"Command:      {info['command']}")
        print(f"Location:     {info['file_path']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Server deployment CLI",
        prog="python -m server",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Deploy a server from a recipe")
    run_parser.add_argument("--recipe", required=True, help="Recipe name to deploy")
    run_parser.add_argument("--count", type=int, default=1, help="Number of instances to launch")

    subparsers.add_parser("list", help="List available server recipes")

    stop_parser = subparsers.add_parser("stop", help="Stop a running server instance")
    stop_parser.add_argument("--name", required=True, help="Instance name to stop")

    subparsers.add_parser("stop-all", help="Stop every tracked server instance")

    subparsers.add_parser("status", help="Show status for tracked server instances")

    info_parser = subparsers.add_parser("info", help="Show information about a recipe")
    info_parser.add_argument("--recipe", required=True, help="Recipe name")

    template_parser = subparsers.add_parser("template", help="Create a recipe template")
    template_parser.add_argument("--name", required=True, help="Template file name")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    handle_server_commands(args)


if __name__ == "__main__":
    main()
