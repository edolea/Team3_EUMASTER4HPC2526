#!/bin/bash -l
# AI-Factories CLI Wrapper
# Usage: ./ai-factories.sh <module> <command> [options]

set -e

# Setup environment
setup_environment() {
    # Load modules if on MeluXina
    if command -v module &> /dev/null; then
        source /usr/share/lmod/lmod/init/bash
        module load env/release/2024.1 2>/dev/null || true
        module load Python/3.12.3-GCCcore-13.3.0 2>/dev/null || true
    fi
    
    # Ensure local bin is in PATH
    export PATH="$HOME/.local/bin:$PATH"
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"
}

# Show usage
show_usage() {
    cat << EOF
AI-Factories CLI

Usage: ./ai-factories.sh <module> <command> [options]

Modules:
  server    Server deployment operations
  client    Client/benchmark operations
  monitor   Monitoring operations

Commands:

  Server:
    server run --recipe <name> [--count <n>]
    server stop --name <instance>
    server stop-all
    server list
    server status
    server info --recipe <name>

  Client:
    client run --recipe <name> [--runs <n>]
    client list
    client info --recipe <name>

  Monitor:
    monitor start --recipe <name> [--targets <job-ids>]
    monitor stop --id <monitor-id>
    monitor stop-all
    monitor list
    monitor status --id <monitor-id>
    monitor info --recipe <name>

Examples:
  # Deploy a vLLM server
  ./ai-factories.sh server run --recipe vllm-server

  # Start monitoring a server
  ./ai-factories.sh monitor start --recipe vllm-monitor --targets 12345

  # Run benchmark
  ./ai-factories.sh client run --recipe vllm-benchmark

  # List all resources
  ./ai-factories.sh server list
  ./ai-factories.sh monitor list

EOF
}

# Main execution
main() {
    setup_environment
    
    if [ $# -eq 0 ]; then
        show_usage
        exit 0
    fi
    
    MODULE="$1"
    shift
    
    case "$MODULE" in
        server|client|monitor)
            python -m our "$MODULE" "$@"
            ;;
        -h|--help|help)
            show_usage
            ;;
        *)
            echo "Error: Unknown module '$MODULE'"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
