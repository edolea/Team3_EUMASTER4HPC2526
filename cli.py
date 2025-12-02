"""
Unified CLI for AI-Factories framework
Combines client, server, and monitor modules
"""

import argparse
import sys
from pathlib import Path

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(
        description="AI-Factories - Unified AI Workload Framework",
        prog="python -m"
    )
    
    subparsers = parser.add_subparsers(dest="module", help="Module to use")
    
    # Client module
    client_parser = subparsers.add_parser("client", help="Client/benchmark operations")
    client_subparsers = client_parser.add_subparsers(dest="command", help="Client commands")
    
    # Client: run
    run_parser = client_subparsers.add_parser("run", help="Run a benchmark")
    run_parser.add_argument("--recipe", required=True, help="Recipe name")
    run_parser.add_argument("--runs", type=int, default=1, help="Number of runs")
    run_parser.add_argument("--output", default="./results", help="Output directory")
    
    # Client: list
    client_subparsers.add_parser("list", help="List available client recipes")
    
    # Client: info
    client_info_parser = client_subparsers.add_parser("info", help="Get recipe info")
    client_info_parser.add_argument("--recipe", required=True, help="Recipe name")
    
    # Server module
    server_parser = subparsers.add_parser("server", help="Server deployment operations")
    server_subparsers = server_parser.add_subparsers(dest="command", help="Server commands")
    
    # Server: run
    server_run_parser = server_subparsers.add_parser("run", help="Deploy a server")
    server_run_parser.add_argument("--recipe", required=True, help="Recipe name")
    server_run_parser.add_argument("--count", type=int, default=1, help="Number of instances")
    
    # Server: list
    server_subparsers.add_parser("list", help="List available server recipes")
    
    # Server: stop
    server_stop_parser = server_subparsers.add_parser("stop", help="Stop a server instance")
    server_stop_parser.add_argument("--name", required=True, help="Instance name")
    
    # Server: stop-all
    server_subparsers.add_parser("stop-all", help="Stop all server instances")
    
    # Server: status
    server_subparsers.add_parser("status", help="Show server status")
    
    # Server: info
    server_info_parser = server_subparsers.add_parser("info", help="Get recipe info")
    server_info_parser.add_argument("--recipe", required=True, help="Recipe name")
    
    # Monitor module
    monitor_parser = subparsers.add_parser("monitor", help="Monitoring operations")
    monitor_subparsers = monitor_parser.add_subparsers(dest="command", help="Monitor commands")
    
    # Monitor: start
    monitor_start_parser = monitor_subparsers.add_parser("start", help="Start monitoring stack")
    monitor_start_parser.add_argument("--recipe", required=True, help="Recipe name")
    monitor_start_parser.add_argument("--targets", help="Comma-separated SLURM job IDs")
    
    # Monitor: stop
    monitor_stop_parser = monitor_subparsers.add_parser("stop", help="Stop a monitor")
    monitor_stop_parser.add_argument("--id", required=True, help="Monitor ID")
    
    # Monitor: list
    monitor_subparsers.add_parser("list", help="List available monitors and running instances")
    
    # Monitor: status
    monitor_status_parser = monitor_subparsers.add_parser("status", help="Get monitor status")
    monitor_status_parser.add_argument("--id", required=True, help="Monitor ID")
    
    # Monitor: stop-all
    monitor_subparsers.add_parser("stop-all", help="Stop all monitors")
    
    # Monitor: info
    monitor_info_parser = monitor_subparsers.add_parser("info", help="Get recipe info")
    monitor_info_parser.add_argument("--recipe", required=True, help="Recipe name")
    
    # Monitor: export
    monitor_export_parser = monitor_subparsers.add_parser("export", help="Export Prometheus metrics to JSON/CSV")
    monitor_export_parser.add_argument("--id", required=True, help="Monitor ID")
    monitor_export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    monitor_export_parser.add_argument("--type", choices=["instant", "range", "all"], default="instant",
                                       help="Export type: instant (current values), range (time-series), all (all metrics)")
    monitor_export_parser.add_argument("--output", help="Output directory (default: logs/monitors/<id>/metrics/)")
    monitor_export_parser.add_argument("--queries", help="Comma-separated custom queries (format: metric:description)")
    monitor_export_parser.add_argument("--start", help="Start time for range queries (RFC3339 or Unix timestamp)")
    monitor_export_parser.add_argument("--end", help="End time for range queries (RFC3339 or Unix timestamp)")
    monitor_export_parser.add_argument("--step", default="15s", help="Step size for range queries (default: 15s)")
    
    args = parser.parse_args()
    
    if not args.module:
        parser.print_help()
        print("\n Available modules: client, server, monitor")
        return
    
    # Route to appropriate module
    if args.module == "client":
        from src.client.__main__ import handle_client_commands
        handle_client_commands(args)
    elif args.module == "server":
        from src.server.__main__ import handle_server_commands
        handle_server_commands(args)
    elif args.module == "monitor":
        from src.monitor.__main__ import handle_monitor_commands
        handle_monitor_commands(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
